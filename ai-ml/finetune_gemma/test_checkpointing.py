"""Unit tests for model checkpointing in finetune_and_evaluate.py."""

import sys
import os
import unittest
import argparse
from unittest.mock import patch, MagicMock

# Add target folder to path to allow importing finetune_and_evaluate
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from finetune_and_evaluate import parse_args, train_model


class TestCheckpointing(unittest.TestCase):
    """Test suite covering model checkpointing configuration and detection mechanics."""

    @patch('sys.argv', ['finetune_and_evaluate.py'])
    def test_checkpointing_argument_parsing_defaults(self):
        """Verify default values for checkpointing arguments."""
        args = parse_args()
        self.assertEqual(args.checkpoint_strategy, 'steps')
        self.assertEqual(args.save_steps, 100)
        self.assertEqual(args.save_total_limit, 2)

    @patch('sys.argv', [
        'finetune_and_evaluate.py',
        '--checkpoint-strategy', 'epoch',
        '--save-steps', '250',
        '--save-total-limit', '5',
        '--output-dir', '/tmp/custom-output'
    ])
    def test_checkpointing_argument_parsing_custom(self):
        """Verify custom values for checkpointing arguments are correctly parsed."""
        args = parse_args()
        self.assertEqual(args.checkpoint_strategy, 'epoch')
        self.assertEqual(args.save_steps, 250)
        self.assertEqual(args.save_total_limit, 5)
        self.assertEqual(args.output_dir, '/tmp/custom-output')

    @patch('finetune_and_evaluate.SFTTrainer')
    @patch('finetune_and_evaluate.SFTConfig')
    @patch('finetune_and_evaluate.LoraConfig')
    @patch('finetune_and_evaluate.os.path.isdir')
    @patch('transformers.trainer_utils.get_last_checkpoint')
    def test_checkpoint_detection_empty_directory(
        self, mock_get_last_checkpoint, mock_isdir, mock_lora_config, mock_sft_config, mock_sft_trainer
    ):
        """Verify resume behavior when the output directory is empty (no checkpoints)."""
        # Configure mocks
        mock_isdir.return_value = True
        mock_get_last_checkpoint.return_value = None

        mock_model = MagicMock()
        mock_processor = MagicMock()
        mock_train_data = MagicMock()
        mock_eval_data = MagicMock()

        args = argparse.Namespace(
            output_dir='/tmp/test-output',
            num_epochs=1,
            batch_size=1,
            gradient_accumulation_steps=1,
            learning_rate=1e-5,
            checkpoint_strategy='steps',
            save_steps=10,
            save_total_limit=2,
            lora_r=8,
            lora_alpha=16,
            lora_dropout=0.05
        )

        # Instantiate mock trainer
        mock_trainer_instance = mock_sft_trainer.return_value
        mock_trainer_instance.model = mock_model

        # Execute training configuration and checkpoint detection
        result_model = train_model(mock_model, mock_processor, mock_train_data, mock_eval_data, args)

        # Assertions
        mock_isdir.assert_called_once_with('/tmp/test-output')
        mock_get_last_checkpoint.assert_called_once_with('/tmp/test-output')

        # Verify SFTConfig was initialized with correct checkpoint strategy parameters
        mock_sft_config.assert_called_once()
        config_kwargs = mock_sft_config.call_args[1]
        self.assertEqual(config_kwargs.get('save_strategy'), 'steps')
        self.assertEqual(config_kwargs.get('save_steps'), 10)
        self.assertEqual(config_kwargs.get('save_total_limit'), 2)

        # Verify trainer.train was called with resume_from_checkpoint=None
        mock_trainer_instance.train.assert_called_once_with(resume_from_checkpoint=None)

        # Verify save_model was called
        mock_trainer_instance.save_model.assert_called_once_with('/tmp/test-output')

        self.assertEqual(result_model, mock_model)

    @patch('finetune_and_evaluate.SFTTrainer')
    @patch('finetune_and_evaluate.SFTConfig')
    @patch('finetune_and_evaluate.LoraConfig')
    @patch('finetune_and_evaluate.os.path.isdir')
    @patch('transformers.trainer_utils.get_last_checkpoint')
    def test_checkpoint_detection_with_existing_checkpoints(
        self, mock_get_last_checkpoint, mock_isdir, mock_lora_config, mock_sft_config, mock_sft_trainer
    ):
        """Verify resume behavior when the output directory has existing checkpoints."""
        # Configure mocks
        mock_isdir.return_value = True
        mock_get_last_checkpoint.return_value = '/tmp/test-output/checkpoint-100'

        mock_model = MagicMock()
        mock_processor = MagicMock()
        mock_train_data = MagicMock()
        mock_eval_data = MagicMock()

        args = argparse.Namespace(
            output_dir='/tmp/test-output',
            num_epochs=1,
            batch_size=1,
            gradient_accumulation_steps=1,
            learning_rate=1e-5,
            checkpoint_strategy='steps',
            save_steps=10,
            save_total_limit=2,
            lora_r=8,
            lora_alpha=16,
            lora_dropout=0.05
        )

        # Instantiate mock trainer
        mock_trainer_instance = mock_sft_trainer.return_value
        mock_trainer_instance.model = mock_model

        # Execute training configuration and checkpoint detection
        result_model = train_model(mock_model, mock_processor, mock_train_data, mock_eval_data, args)

        # Assertions
        mock_isdir.assert_called_once_with('/tmp/test-output')
        mock_get_last_checkpoint.assert_called_once_with('/tmp/test-output')

        # Verify SFTConfig was initialized with correct checkpoint strategy parameters
        mock_sft_config.assert_called_once()
        config_kwargs = mock_sft_config.call_args[1]
        self.assertEqual(config_kwargs.get('save_strategy'), 'steps')
        self.assertEqual(config_kwargs.get('save_steps'), 10)
        self.assertEqual(config_kwargs.get('save_total_limit'), 2)

        # Verify trainer.train was called with resume_from_checkpoint set to the latest checkpoint path
        mock_trainer_instance.train.assert_called_once_with(resume_from_checkpoint='/tmp/test-output/checkpoint-100')

        # Verify save_model was called
        mock_trainer_instance.save_model.assert_called_once_with('/tmp/test-output')

        self.assertEqual(result_model, mock_model)

    @patch('finetune_and_evaluate.SFTTrainer')
    @patch('finetune_and_evaluate.SFTConfig')
    @patch('finetune_and_evaluate.LoraConfig')
    @patch('finetune_and_evaluate.os.path.isdir')
    @patch('transformers.trainer_utils.get_last_checkpoint')
    def test_checkpoint_detection_disabled(
        self, mock_get_last_checkpoint, mock_isdir, mock_lora_config, mock_sft_config, mock_sft_trainer
    ):
        """Verify behavior when checkpoint strategy is set to 'no'."""
        mock_isdir.return_value = True

        mock_model = MagicMock()
        mock_processor = MagicMock()
        mock_train_data = MagicMock()
        mock_eval_data = MagicMock()

        args = argparse.Namespace(
            output_dir='/tmp/test-output',
            num_epochs=1,
            batch_size=1,
            gradient_accumulation_steps=1,
            learning_rate=1e-5,
            checkpoint_strategy='no',
            save_steps=10,
            save_total_limit=2,
            lora_r=8,
            lora_alpha=16,
            lora_dropout=0.05
        )

        # Instantiate mock trainer
        mock_trainer_instance = mock_sft_trainer.return_value
        mock_trainer_instance.model = mock_model

        # Execute training configuration and checkpoint detection
        result_model = train_model(mock_model, mock_processor, mock_train_data, mock_eval_data, args)

        # Verify get_last_checkpoint was NOT called
        mock_get_last_checkpoint.assert_not_called()

        # Verify SFTConfig was initialized with correct checkpoint strategy parameters
        mock_sft_config.assert_called_once()
        config_kwargs = mock_sft_config.call_args[1]
        self.assertEqual(config_kwargs.get('save_strategy'), 'no')
        self.assertIsNone(config_kwargs.get('save_total_limit'))

        # Verify trainer.train was called with resume_from_checkpoint=None
        mock_trainer_instance.train.assert_called_once_with(resume_from_checkpoint=None)


if __name__ == '__main__':
    unittest.main()
