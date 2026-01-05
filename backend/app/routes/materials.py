"""
Materials API Routes.

Provides endpoints for material library access.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from backend.app.models import MaterialInfo
from library.material_registry import MaterialRegistry

router = APIRouter()


@router.get("/", response_model=List[MaterialInfo])
async def list_materials(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """List all materials from the registry."""
    registry = MaterialRegistry.get()
    
    materials = []
    for mat_id, prop in registry.materials.items():
        info = MaterialInfo(
            id=mat_id,
            name=prop.name,
            lambda_val=prop.lambda_val,
            color=prop.color,
            category=prop.category,
            source=prop.source
        )
        
        if category is None or prop.category == category:
            materials.append(info)
    
    return sorted(materials, key=lambda m: (m.category or "", m.name))


@router.get("/categories")
async def list_categories():
    """List all material categories."""
    registry = MaterialRegistry.get()
    
    categories = set()
    for prop in registry.materials.values():
        if prop.category:
            categories.add(prop.category)
    
    return {"categories": sorted(categories)}


@router.get("/{material_id}", response_model=MaterialInfo)
async def get_material(material_id: str):
    """Get a specific material by ID."""
    registry = MaterialRegistry.get()
    
    prop = registry.get_by_id(material_id)
    if not prop:
        raise HTTPException(status_code=404, detail=f"Material '{material_id}' not found")
    
    return MaterialInfo(
        id=material_id,
        name=prop.name,
        lambda_val=prop.lambda_val,
        color=prop.color,
        category=prop.category,
        source=prop.source
    )


@router.get("/lookup/lambda/{material_id}")
async def get_lambda(material_id: str, default: float = 0.0):
    """Get thermal conductivity for a material."""
    registry = MaterialRegistry.get()
    lambda_val = registry.get_lambda(material_id, default)
    return {"material_id": material_id, "lambda": lambda_val}
