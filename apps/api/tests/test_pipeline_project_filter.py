"""Pipeline project options come from Projects, not from the leads on screen."""

from uuid import uuid4

from sqlalchemy import select

from investhome_api.models.inventory import ProjectPhase
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.project import DevelopmentType, Project, ProjectStatus, ProjectType
from investhome_api.services.crm.crm_lead_service import _filter_options, list_crm_leads
from investhome_api.services.crm.person_project_membership import list_membership_projects


def _project(db, *, code: str, name: str) -> Project:
    project = Project(
        project_code=code,
        project_name=name,
        project_type=ProjectType.RESIDENTIAL,
        development_type=DevelopmentType.GROUND_UP,
        project_status=ProjectStatus.CONSTRUCTION,
    )
    db.add(project)
    db.flush()
    return project


def test_project_filter_lists_every_project_and_respects_phase(db):
    temple = _project(db, code=f"PRJ-T-{uuid4().hex[:8]}", name="The Temple")
    quiet = _project(db, code=f"PRJ-Q-{uuid4().hex[:8]}", name="Quiet Project")
    historic = ProjectPhase(project_id=temple.id, name="Historic", display_order=0, active=True)
    addition = ProjectPhase(project_id=temple.id, name="Addition", display_order=1, active=True)
    db.add_all([historic, addition])
    db.flush()
    historic_lead = Lead(
        full_name="Historic Person",
        status=LeadStatus.NEW,
        interested_project="The Temple",
        project_id=temple.id,
        phase_id=historic.id,
        is_demo=False,
    )
    addition_lead = Lead(
        full_name="Addition Person",
        status=LeadStatus.NEW,
        interested_project="The Temple",
        project_id=temple.id,
        phase_id=addition.id,
        is_demo=False,
    )
    text_only = Lead(
        full_name="Text Only",
        status=LeadStatus.NEW,
        interested_project="The Temple",
        is_demo=False,
    )
    db.add_all([historic_lead, addition_lead, text_only])
    db.commit()

    _sources, projects, _owners = _filter_options(db)
    assert "The Temple" in projects
    assert "Quiet Project" in projects

    catalog = list_membership_projects(db)
    quiet_option = next(item for item in catalog if item["project_id"] == str(quiet.id))
    assert quiet_option["phases"] == []

    historic_page = list_crm_leads(db, project=str(temple.id), phase_id=historic.id, page_size=50)
    names = {item.full_name for item in historic_page.items}
    assert historic_page.total >= 1
    assert "Historic Person" in names
    assert "Addition Person" not in names
    assert "Text Only" not in names

    quiet_page = list_crm_leads(db, project=str(quiet.id), page_size=50)
    assert quiet_page.total == 0
    assert quiet_page.items == []
    assert db.scalar(select(Lead.id).where(Lead.full_name == "Text Only")) is not None
