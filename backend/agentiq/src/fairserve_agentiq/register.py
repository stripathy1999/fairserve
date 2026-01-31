import logging
from typing import Dict


try:
    from nat.builder.builder import Builder
    from nat.builder.function_info import FunctionInfo
    from nat.cli.register_workflow import register_function
    from nat.data_models.function import FunctionBaseConfig
except ImportError:  # pragma: no cover
    from aiq.builder.builder import Builder  # type: ignore
    from aiq.builder.function_info import FunctionInfo  # type: ignore
    from aiq.cli.register_workflow import register_function  # type: ignore
    from aiq.data_models.function import FunctionBaseConfig  # type: ignore

from .workflow import (
    memo_step,
    propose_step,
    rank_step,
    redteam_step,
    retrieve_step,
    simulate_step,
    verify_step,
)

logger = logging.getLogger(__name__)






class FairServeProposeConfig(FunctionBaseConfig, name="fairserve_propose"):
    description: str = "Propose policies from a city state."


class FairServeRetrieveConfig(FunctionBaseConfig, name="fairserve_retrieve"):
    description: str = "Retrieve evidence cards from city metrics."


class FairServeSimulateConfig(FunctionBaseConfig, name="fairserve_simulate"):
    description: str = "Run simulation for each proposed policy."


class FairServeVerifyConfig(FunctionBaseConfig, name="fairserve_verify"):
    description: str = "Verify simulated policies against governance constraints."


class FairServeRankConfig(FunctionBaseConfig, name="fairserve_rank"):
    description: str = "Rank policies deterministically using quant metrics."


class FairServeRedTeamConfig(FunctionBaseConfig, name="fairserve_redteam"):
    description: str = "Red-team risk review based on sim + verify results."


class FairServeMemoConfig(FunctionBaseConfig, name="fairserve_memo"):
    description: str = "Executive memo based on selected policy and evidence."


@register_function(config_type=FairServeProposeConfig)
async def fairserve_propose(config: FairServeProposeConfig, builder: Builder):
    async def _inner(payload: dict) -> dict:
        return {"payload": propose_step(payload)}

    yield FunctionInfo.from_fn(_inner, description=config.description)


@register_function(config_type=FairServeRetrieveConfig)
async def fairserve_retrieve(config: FairServeRetrieveConfig, builder: Builder):
    async def _inner(payload: dict) -> dict:
        return {"payload": retrieve_step(payload)}

    yield FunctionInfo.from_fn(_inner, description=config.description)


@register_function(config_type=FairServeSimulateConfig)
async def fairserve_simulate(config: FairServeSimulateConfig, builder: Builder):
    async def _inner(payload: dict) -> dict:
        return {"payload": simulate_step(payload)}

    yield FunctionInfo.from_fn(_inner, description=config.description)


@register_function(config_type=FairServeVerifyConfig)
async def fairserve_verify(config: FairServeVerifyConfig, builder: Builder):
    async def _inner(payload: dict) -> dict:
        return {"payload": verify_step(payload)}

    yield FunctionInfo.from_fn(_inner, description=config.description)


@register_function(config_type=FairServeRankConfig)
async def fairserve_rank(config: FairServeRankConfig, builder: Builder):
    async def _inner(payload: dict) -> dict:
        return {"payload": rank_step(payload)}

    yield FunctionInfo.from_fn(_inner, description=config.description)


@register_function(config_type=FairServeRedTeamConfig)
async def fairserve_redteam(config: FairServeRedTeamConfig, builder: Builder):
    async def _inner(payload: dict) -> dict:
        return {"payload": redteam_step(payload)}

    yield FunctionInfo.from_fn(_inner, description=config.description)


@register_function(config_type=FairServeMemoConfig)
async def fairserve_memo(config: FairServeMemoConfig, builder: Builder):
    async def _inner(payload: dict) -> dict:
        return {"payload": memo_step(payload)}

    yield FunctionInfo.from_fn(_inner, description=config.description)
