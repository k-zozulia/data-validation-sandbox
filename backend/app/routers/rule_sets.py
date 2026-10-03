"""Saved, reusable rule sets."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppException, not_found
from app.models.orm import RuleSet
from app.models.schemas import RuleSetIn, RuleSetOut, RuleSetUpdate
from app.services.yaml_generator import parse_rules_yaml

router = APIRouter(prefix="/rule-sets", tags=["rule sets"])


def _get(db: Session, rule_set_id: str) -> RuleSet:
    rs = db.get(RuleSet, rule_set_id)
    if rs is None:
        raise not_found("rule_set")
    return rs


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppException(409, "name_taken", "A rule set with this name already exists")


@router.get("", response_model=list[RuleSetOut])
def list_rule_sets(db: Session = Depends(get_db)):
    return db.scalars(select(RuleSet).order_by(RuleSet.updated_at.desc())).all()


@router.post("", response_model=RuleSetOut, status_code=201)
def create_rule_set(body: RuleSetIn, db: Session = Depends(get_db)):
    parse_rules_yaml(body.rules_yaml)                     # reject broken YAML early
    rs = RuleSet(name=body.name.strip(), description=body.description,
                 rules_yaml=body.rules_yaml)
    db.add(rs)
    _commit(db)
    return rs


@router.get("/{rule_set_id}", response_model=RuleSetOut)
def get_rule_set(rule_set_id: str, db: Session = Depends(get_db)):
    return _get(db, rule_set_id)


@router.patch("/{rule_set_id}", response_model=RuleSetOut)
def update_rule_set(rule_set_id: str, body: RuleSetUpdate, db: Session = Depends(get_db)):
    rs = _get(db, rule_set_id)
    if body.rules_yaml is not None:
        parse_rules_yaml(body.rules_yaml)
        rs.rules_yaml = body.rules_yaml
    if body.name is not None:
        rs.name = body.name.strip()
    if body.description is not None:
        rs.description = body.description
    _commit(db)
    return rs


@router.delete("/{rule_set_id}", status_code=204)
def delete_rule_set(rule_set_id: str, db: Session = Depends(get_db)):
    db.delete(_get(db, rule_set_id))
    db.commit()
