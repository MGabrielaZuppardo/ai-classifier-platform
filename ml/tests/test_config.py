import pytest

from ml.config import InvalidConfigError, TrainingConfig


def test_defaults_follow_the_agreed_mvp_values():
    config = TrainingConfig()

    assert (config.model, config.epochs, config.batch_size) == ("resnet18", 20, 64)
    assert config.optimizer == "adamw"
    assert config.early_stopping_patience == 5
    assert config.fine_tune is True


def test_json_roundtrip_preserves_the_config():
    config = TrainingConfig(model="cnn_baseline", pretrained=False, seed=7, epochs=3)

    assert TrainingConfig.from_json(config.to_json()) == config


@pytest.mark.parametrize(
    "overrides",
    [
        {"epochs": 0},
        {"epochs": 51},
        {"batch_size": 257},
        {"learning_rate": 0},
        {"weight_decay": -1},
        {"early_stopping_patience": -1},
        {"model": "vgg"},
        {"optimizer": "adam"},
    ],
)
def test_out_of_range_values_are_rejected(overrides: dict):
    with pytest.raises(InvalidConfigError):
        TrainingConfig(**overrides)


def test_unknown_fields_are_rejected():
    with pytest.raises(InvalidConfigError):
        TrainingConfig.from_dict({"epochs": 3, "run_this": "import os"})
