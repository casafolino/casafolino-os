# -*- coding: utf-8 -*-
from . import models
from . import controllers


def _post_init_hook(env):
    from .data.workspace_project_seed_hook import seed_projects
    seed_projects(env)


def _uninstall_hook(env):
    pass
