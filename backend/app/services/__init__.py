"""Builds one adapter per external tool from Settings modes. The only place real-vs-fake is decided."""

from dataclasses import dataclass

from app.config import Mode, Settings
from app.services.browserbase import Browserbase, FakeBrowserbase, RealBrowserbase
from app.services.coding_agent import CodingAgent, FakeCodingAgent, RealCodingAgent
from app.services.github import FakeGitHub, GitHub, RealGitHub
from app.services.jev import FakeJev, Jev, RealJev
from app.services.llm import FakeLLM, GmiLLM, LLM
from app.services.photon import FakePhoton, Photon, RealPhoton


@dataclass
class Services:
    jev: Jev
    llm: LLM
    photon: Photon
    browserbase: Browserbase
    github: GitHub
    agent: CodingAgent


def _secret(s) -> str:
    return s.get_secret_value()


def build_services(cfg: Settings) -> Services:
    """Assumes cfg.validate_startup() already passed, so real-mode keys are present."""
    real = Mode.real
    return Services(
        jev=RealJev(_secret(cfg.typesafe_api_key), cfg.jev_model) if cfg.jev_mode is real else FakeJev(),
        llm=GmiLLM(_secret(cfg.gmi_api_key), cfg.gmi_base_url, cfg.gmi_model) if cfg.llm_mode is real else FakeLLM(),
        photon=RealPhoton(cfg.photon_project_id, _secret(cfg.photon_secret)) if cfg.photon_mode is real else FakePhoton(),
        browserbase=(
            RealBrowserbase(_secret(cfg.browserbase_api_key), cfg.browserbase_project_id)
            if cfg.browserbase_mode is real else FakeBrowserbase()
        ),
        github=(
            RealGitHub(_secret(cfg.github_token), cfg.github_repo, cfg.github_base_branch)
            if cfg.github_mode is real else FakeGitHub()
        ),
        agent=(
            RealCodingAgent(_secret(cfg.gmi_api_key), cfg.gmi_base_url, cfg.gmi_model)
            if cfg.agent_mode is real else FakeCodingAgent()
        ),
    )
