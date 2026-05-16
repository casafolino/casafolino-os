# -*- coding: utf-8 -*-
"""
Cleanup all DEMO- prefixed records from folinofood.
Run via: docker exec odoo-app odoo shell -d folinofood --no-http < /home/ubuntu/cleanup_demo_dataset.py
Order: respect FK constraints (children before parents).
"""

print("=== DEMO DATA CLEANUP ===\n")

# 1. Network actors (FK to project.project)
actors = env['cf.dossier.actor'].search([('project_id.name', 'like', 'DEMO-%')])
print(f"Actors: {len(actors)} found")
if actors:
    actors.unlink()

# 2. Leads (FK to project.project via cf_project_id)
leads = env['crm.lead'].search([('name', 'like', 'DEMO-%')])
print(f"Leads: {len(leads)} found")
if leads:
    leads.unlink()

# 3. Samples
samples = env['cf.export.sample'].search([('reference', 'like', 'DEMO-%')])
print(f"Samples: {len(samples)} found")
if samples:
    samples.unlink()

# 4. Tasks of demo dossiers
tasks = env['project.task'].search([('project_id.name', 'like', 'DEMO-%')])
print(f"Tasks: {len(tasks)} found")
if tasks:
    tasks.unlink()

# 5. Unlink dossiers from initiatives before deleting
dossiers = env['project.project'].search([('name', 'like', 'DEMO-%')])
if dossiers:
    dossiers.write({'initiative_id': False})

# 6. Initiatives
initiatives = env['cf.initiative'].search([('name', 'like', 'DEMO-%')])
print(f"Initiatives: {len(initiatives)} found")
if initiatives:
    initiatives.unlink()

# 7. Dossiers (project.project)
print(f"Dossiers: {len(dossiers)} found")
if dossiers:
    dossiers.unlink()

# 8. Partners (buyers, brokers, clients — all have DEMO- prefix)
partners = env['res.partner'].search([('name', 'like', 'DEMO-%')])
print(f"Partners: {len(partners)} found")
if partners:
    partners.unlink()

env.cr.commit()
print("\n✓ Demo data cleanup done.")
