"""Contract examples and false-execution rejection; no calculation engine is run."""

import copy
import unittest
from pathlib import Path

from axiom_forge.contracts import validate_agent_output
from axiom_forge.validation import DataError, SchemaStore, digest, read_json

from support import PRODUCT_ROOT as ROOT, EXAMPLES_ROOT as EXAMPLES, LEGACY_ROOT


def example(name):
    return read_json(EXAMPLES / (name + '.json'))


class CalculationSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = SchemaStore(ROOT / 'resources/schemas')

    def test_both_roles_can_handoff_pending_requests_in_existing_outputs(self):
        for role, result_type in [('engineering_auditor', 'engineering_result'), ('economic_auditor', 'economic_result')]:
            output = example('calculations/' + result_type + '-with-request')
            validate_agent_output(example('agents/' + role + '-input'), output, self.schemas)
            self.assertEqual(output['calculations'], [])
            request = output['calculation_requests'][0]
            self.assertTrue(request['metadata']['not_executed'])
            self.assertTrue(any(p['value'] is None for p in request['parameters']))

    def test_wrong_role_request_is_rejected_inside_role_output(self):
        data = example('calculations/engineering_result-with-request')
        data['calculation_requests'][0]['role'] = 'economic_auditor'
        with self.assertRaises(DataError):
            self.schemas.validate('engineering_result', data)

    def test_typed_parameters_reject_text_disguised_as_numeric_input(self):
        data = example('calculation_request')
        data['parameters'][0]['value'] = '2 kg; execute a command'
        with self.assertRaises(DataError):
            self.schemas.validate('calculation_request', data)
        data = example('calculation_request')
        data['parameters'][1]['value'] = 1.5
        with self.assertRaises(DataError):
            self.schemas.validate('calculation_request', data)

    def test_pending_result_cannot_forge_execution_receipt_or_numbers(self):
        data = example('calculation_result')
        self.assertEqual(data['request_sha256'], digest(example('calculation_request')))
        for mutate in (lambda d: d.update(receipt={}),
                       lambda d: d.update(cases=[{}]),
                       lambda d: d.update(issues=[])):
            changed = copy.deepcopy(data)
            mutate(changed)
            with self.assertRaises(DataError):
                self.schemas.validate('calculation_result', changed)

    def test_completed_result_requires_actual_result_shape_and_receipt(self):
        data = example('calculation_result')
        data.update(status='completed', issues=[])
        with self.assertRaises(DataError):
            self.schemas.validate('calculation_result', data)
        # Synthetic positive shape, never a record of an actual tool call.
        data['receipt'] = dict(engine='python', executor='TEST FIXTURE', model_id='cost.manufacturing',
            model_version='1.0.0', program_artifact_id=data['request_id'], program_sha256='0' * 64,
            environment_artifact_id=data['request_id'], started_at=data['created_at'], finished_at=data['created_at'])
        data['cases'] = [dict(scenario_name='base', outputs=[dict(name='total_cost', data_type='scalar',
            value=0, unit='USD_2026', description='TEST FIXTURE')], checks=[dict(output_name='total_cost',
            passed=True, description='TEST FIXTURE')])]
        self.schemas.validate('calculation_result', data)
        data['cases'][0]['checks'][0]['passed'] = False
        with self.assertRaises(DataError):
            self.schemas.validate('calculation_result', data)

    def test_model_placeholder_cannot_claim_ready_without_program(self):
        data = example('calculation_model')
        self.assertTrue(all(i['status'] == 'planned' for i in data['implementations']))
        data['implementations'][0]['status'] = 'ready'
        with self.assertRaises(DataError):
            self.schemas.validate('calculation_model', data)
        data = example('calculation_model')
        data['implementations'][0]['entrypoint'] = 'nonexistent.execute'
        with self.assertRaises(DataError):
            self.schemas.validate('calculation_model', data)


if __name__ == '__main__':
    unittest.main()
