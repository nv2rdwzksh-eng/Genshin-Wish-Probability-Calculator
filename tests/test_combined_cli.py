import contextlib
import io
import unittest

from genshin_wish.cli import main, run_banner_interactive


class CombinedCliTests(unittest.TestCase):
    def test_combined_argument_report_and_exact_inverse(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main([
                '--banner', 'combined', '--wishes', '2', '--pity', '89',
                '--target', '1', '--capturing-radiance', '--cr-counter', '3',
                '--weapon-pity', '79', '--weapon-guaranteed', '--fate-point', '1',
                '--weapon-target', '1', '--confidence', '100', '--threshold-table',
            ])
        text = output.getvalue()
        self.assertIn('All goals completed: 100.00000000%', text)
        self.assertIn('Character completed, weapon not completed: 0.00000000%', text)
        self.assertIn('Character not completed: 0.00000000%', text)
        self.assertIn('community CR hidden-counter assumption', text)
        self.assertIn('Minimum total wishes for at least 100.00% combined success: 2', text)
        self.assertIn('Probability target', text)

    def test_existing_copy_flags_allow_already_completed_targets(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main([
                '--banner', 'combined', '--wishes', '0', '--pity', '0',
                '--target', '2', '--character-copies', '2',
                '--weapon-pity', '0', '--weapon-target', '3', '--weapon-copies', '4',
            ])
        self.assertIn('All goals completed: 100.00000000%', output.getvalue())

    def test_combined_interactive_retries_inputs_and_confidence(self):
        responses = iter((
            '3', '-1', '2',                       # combined, budget retry
            '90', '89', 'n', '1', '', 'cr', '3',  # character state/target/model
            '79', 'y', '1', '1', '', '2',         # weapon state/target/model
            '101', '100',                        # confidence retry
        ))
        output = []
        run_banner_interactive(input_fn=lambda _: next(responses), output_fn=output.append)
        text = '\n'.join(output)
        self.assertIn('All goals completed: 100.00000000%', text)
        self.assertIn('Minimum total wishes for at least 100.00% combined success: 2', text)
        self.assertEqual(sum(line.startswith('Invalid input:') for line in output), 3)

    def test_missing_combined_flags_and_invalid_inputs_rejected(self):
        base = [
            '--banner', 'combined', '--wishes', '10', '--pity', '0', '--target', '1',
            '--weapon-pity', '0', '--weapon-target', '1',
        ]
        for extra in (
            ['--weapon-pity', '80'], ['--cr-counter', '4'], ['--wishes', '-1'],
            ['--weapon-target', '-1'], ['--character-copies', '-1'],
            ['--fate-point', '2'], ['--confidence', '101'],
            ['--mode', 'full-distribution'],
        ):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main(base + extra)
            self.assertEqual(error.exception.code, 2)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(['--banner', 'combined', '--wishes', '10'])


if __name__ == '__main__':
    unittest.main()
