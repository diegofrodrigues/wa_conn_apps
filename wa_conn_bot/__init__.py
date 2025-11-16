# -*- coding: utf-8 -*-
from . import models

def post_init_hook(env):
    """Post-installation hook to integrate with providers"""
    from .models import wa_provider_evolution
    wa_provider_evolution.post_init_hook(env)
