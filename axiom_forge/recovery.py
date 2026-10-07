"""Validate archived invocations before reusing results; never construct an SDK."""

import copy
from decimal import Decimal
from types import SimpleNamespace

from .contracts import IDENTITY, OUTPUTS, validate_output_artifacts
from .journal import load, source_fingerprint
from .runtimes.core import ToolBinding
from .tools.storage import safe_relative
from .validation import DataError, digest


class Recovery:
    def __init__(self, runner, initial, control):
        self.runner, self.initial = runner, initial
        self.control = copy.deepcopy(control)
        runner.world.validate_world(initial["world_id"])
        runner.world.validate_binding(initial["metadata"].get("workspace_binding"))
        if (control['host_config_sha256'] != runner.config_sha256
                or control['policy_sha256'] != runner.router.sha256
                or control['source_sha256'] != source_fingerprint(runner.engine_root)):
            raise DataError('Recovery requires the original host config, policy and instructions/schemas')
        self.inputs, self.packets, self.slots = {}, {}, {}
        for attempt in control['attempts']:
            arn = attempt['agent_run_id']
            if arn in self.inputs: raise DataError('Duplicate reserved invocation')
            expected = f".axiom/local/tasks/{initial['task_id']}/inputs/{arn}.json"
            if attempt['input_path'] != expected: raise DataError('Reserved input path differs')
            data = load(runner.repo / safe_relative(expected))
            runner.store.validate_input(data)
            if (digest(data) != attempt['input_sha256'] or data['agent_run_id'] != arn
                    or any(data[k] != initial[k] for k in ('world_id', 'task_id', 'canon_version', 'canon_snapshot', 'user_question', 'task_type'))
                    or data['run_id'] != control['run_id']
                    or (data['role'], data['stage']) != (attempt['role'], attempt['stage'])):
                raise DataError('Reserved input context/hash differs')
            mid = attempt['route'].get('model_id')
            profile = runner.config['profiles'].get(mid)
            if (profile is None or Decimal(attempt['amount_usd']) != Decimal(str(profile['max_cost_usd']))
                    or attempt['route'].get('agent_run_id') != arn
                    or attempt['route'].get('role') != data['role'] or attempt['route'].get('stage') != data['stage']):
                raise DataError('Reservation differs from the trusted model allowance')
            self.inputs[arn] = data
            slot = (data['role'], data['stage'])
            if slot in self.slots and self.slots[slot]['status'] == 'completed':
                raise DataError('A completed role must not have a later attempt')
            self.slots[slot] = attempt
            path = f'.axiom/local/runtime-runs/{arn}/completion.json'
            if attempt['packet_path'] not in (None, path): raise DataError('Completion path differs')
            if (runner.repo / path).exists():
                packet = load(runner.repo / path)
                if attempt['packet_sha256'] is not None and digest(packet) != attempt['packet_sha256']:
                    raise DataError('Archived completion hash differs')
                self.validate_packet(data, packet, profile)
                self.packets[arn] = packet
                if attempt['status'] != 'reserved' and attempt['status'] != packet['agent_run']['status']:
                    raise DataError('Completion status differs from checkpoint')
            elif attempt['status'] == 'completed' or attempt['packet_sha256'] is not None:
                raise DataError('Sealed completion is missing')
        # Budget cannot be made smaller by dropping old unknown or failed calls.
        self.reserved = sum((Decimal(a['amount_usd']) for a in control['attempts']), Decimal(0))

    def validate_packet(self, data, packet, profile):
        required = {'stage', 'agent_run', 'artifact', 'result', 'error', 'tool_artifacts', 'calculation_request_artifacts'}
        if set(packet) != required: raise DataError('Invalid archived Runtime completion')
        agent = packet['agent_run']
        schemas = self.runner.store.schemas
        schemas.validate('agent_run', agent)
        if (packet['stage'] != data['stage'] or agent['role'] != data['role']
                or any(agent[k] != data[k] for k in IDENTITY)
                or agent['metadata'].get('input_sha256') != digest(data)
                or any(agent['metadata'].get(k) != profile[k] for k in ('provider', 'model'))
                or agent['metadata'].get('stage') != data['stage']
                or agent['metadata'].get('workspace_binding') != self.runner.world.binding):
            raise DataError('Archived completion identity/provider/input differs')
        if agent['status'] not in ('completed', 'failed', 'cancelled') or agent['finished_at'] is None:
            raise DataError('Archived Runtime has no finished status')
        receipts = []
        artifacts = [*packet['tool_artifacts'], *packet['calculation_request_artifacts']]
        if agent['status'] == 'completed':
            if packet['artifact'] is None or packet['result'] is None or packet['error'] is not None:
                raise DataError('Completed invocation has no valid output')
            artifacts.insert(0, packet['artifact'])
        elif packet['artifact'] is not None or packet['result'] is not None or packet['calculation_request_artifacts']:
            raise DataError('Uncompleted invocation cannot carry a finished output')
        for artifact in artifacts:
            schemas.validate('artifact', artifact)
            if any(artifact[k] != data[k] for k in ('world_id', 'task_id', 'run_id', 'agent_run_id')):
                raise DataError('Archived artifact belongs to another invocation')
            value = load(self.runner.repo / safe_relative(artifact['path']))
            if digest(value) != artifact['sha256']: raise DataError('Archived artifact content differs')
            if artifact in packet['tool_artifacts']:
                if artifact['path'] != f".axiom/local/tool-runs/{data['agent_run_id']}/receipts/{artifact['artifact_id']}.json":
                    raise DataError('Tool receipt location differs')
                schemas.validate('tool_result', value)
                if value['result_id'] != artifact['artifact_id'] or value['status'] != 'completed':
                    raise DataError('Tool receipt identity/status differs')
                if any(value[k] != data[k] for k in ('world_id', 'task_id', 'run_id', 'agent_run_id', 'canon_version')):
                    raise DataError('Tool receipt context differs')
                if value['receipt']['payload_sha256'] != digest({k: value[k] for k in ('status', 'data', 'error')}):
                    raise DataError('Tool receipt payload hash differs')
                receipts.append(value)
        if agent['status'] == 'completed':
            artifact = packet['artifact']
            if (artifact['artifact_id'] != data['artifact_id']
                    or artifact['kind'] != OUTPUTS[data['role']]
                    or artifact['path'] != f".axiom/local/runtime-runs/{data['agent_run_id']}/output.json"
                    or artifact['sha256'] != digest(packet['result'])):
                raise DataError('Archived output binding differs')
            validate_output_artifacts(data, packet['result'], schemas, packet['tool_artifacts'])
            # Reuse the existing provenance validator with archived receipts only.
            binding = object.__new__(ToolBinding)
            binding.session = SimpleNamespace(context=data)
            binding.receipts = receipts
            binding.validate_provenance(packet['result'])
            requests = packet['result'].get('calculation_requests', [])
            if len({r['request_id'] for r in requests}) != len(requests) or data['artifact_id'] in {r['request_id'] for r in requests}:
                raise DataError('Duplicate calculation request/output IDs')
            if {r['request_id'] for r in requests} != {a['artifact_id'] for a in packet['calculation_request_artifacts']}:
                raise DataError('Archived calculation requests differ')
            for request in requests:
                if any(request[k] != data[k] for k in (*IDENTITY[:4], 'canon_version', 'role')):
                    raise DataError('Archived calculation request context differs')
                ref = next(a for a in packet['calculation_request_artifacts'] if a['artifact_id'] == request['request_id'])
                if (ref['path'] != f".axiom/local/runtime-runs/{data['agent_run_id']}/calculations/{request['request_id']}.json"
                        or ref['sha256'] != digest(request)):
                    raise DataError('Archived calculation request binding differs')

    def attempt(self, role, stage): return self.slots.get((role, stage))

    def completed(self, role, stage):
        attempt = self.attempt(role, stage)
        packet = self.packets.get(attempt['agent_run_id']) if attempt else None
        return packet if packet is not None and packet['agent_run']['status'] == 'completed' else None

    def check_input(self, data):
        attempt = self.attempt(data['role'], data['stage'])
        if attempt:
            original = self.inputs[attempt['agent_run_id']]
            normalized = copy.deepcopy(data)
            for key in ('agent_run_id', 'artifact_id'): normalized[key] = original[key]
            if digest(normalized) != digest(original):
                raise DataError('Reconstructed invocation differs from reserved context')
