# casafolino_console_access — ACL scoped per gli utenti di servizio della Console.
# S0: console_prod_rw (internal, dormiente). Questa slice: console_api (portal, no seat)
# con gateway triage sudo + audit delle scritture.
from . import models
