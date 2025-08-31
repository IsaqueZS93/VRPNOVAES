# file: C:\Users\Novaes Engenharia\github - deploy\VRP\backend\VRP_MODEL\schemas.py
"""
Pydantic models para validar entradas vindas do Streamlit.
Usado em Screen_Checklist_Form e Photo uploader.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, List

ServiceType = Literal['Manutenção Preventiva','Manutenção Preditiva','Manutenção Corretiva','Ajuste e Aferição']
VRPType = Literal['Ação Direta','Auto-Regulada','Pilotada']

# Lista de locais DMC para seleção
DMC_LOCATIONS = [
    'DMC - Salvador Calmon',
    'DMC - Inácio Gracindo',
    'DMC - TV. Nazaré',
    'DMC - TV. Dona Constança',
    'DMC - Praça da Bíblia',
    'DMC - José Carneiro',
    'DMC - Soldado José Guilherme',
    'DMC - Carlos Tenório',
    'DMC - Sampaio Luz',
    'DMC - José Lages',
    'DMC - PIO XII',
    'DMC - Pretestato Ferreira',
    'DMC - Gustavo Paiva',
    'DMC - Paulina Mendonça',
    'DMC - Aloísio Branco',
    'DMC - Benedito Bentes - UPA',
    'DMC - Benedito Bentes - Escola',
    'DMC - Benedito Bentes - Posto'
]

class VRPSite(BaseModel):
    municipality: str = Field(..., description="Município onde a VRP está localizada")
    city: str = Field(..., description="Local DMC da VRP")
    place: str = ""
    brand: str = ""
    type: VRPType
    dn: int = Field(..., description="DN em mm, entre {50,60,85,100,150,200,250,300,350}")
    access_install: Literal['passeio','rua']
    traffic: Literal['alto','baixo']
    lids: Literal['visiveis','cobertas']
    notes_access: str = ""
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude em graus decimais (-90 a 90)")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude em graus decimais (-180 a 180)")
    network_depth_cm: Optional[float] = Field(None, ge=0, le=1000, description="Profundidade da rede em cm (0 a 1000)")
    has_automation: bool = Field(False, description="VRP possui automação/telemetria")

    @validator("dn")
    def dn_allowed(cls, v):
        if v not in {50,60,85,100,150,200,250,300,350}:
            raise ValueError("DN inválido")
        return v

    @validator("latitude", "longitude")
    def validate_coordinates(cls, v):
        if v is not None:
            if not isinstance(v, (int, float)):
                raise ValueError("Coordenada deve ser um número")
        return v

    @validator("city")
    def validate_city(cls, v):
        if v not in DMC_LOCATIONS:
            raise ValueError(f"Cidade deve ser um dos locais DMC: {', '.join(DMC_LOCATIONS)}")
        return v

    @validator("network_depth_cm")
    def validate_network_depth(cls, v):
        if v is not None:
            if not isinstance(v, (int, float)) or v < 0 or v > 1000:
                raise ValueError("Profundidade deve ser um número entre 0 e 1000 cm")
        return v

class Checklist(BaseModel):
    date: str
    service_type: ServiceType
    contractor_id: Optional[int]
    contracted_id: Optional[int]
    team_id: Optional[int]
    vrp_site_id: Optional[int]
    has_reg_upstream: bool = False
    has_reg_downstream: bool = False
    has_bypass: bool = False
    notes_hydraulics: str = ""
    p_up_before: Optional[float]
    p_down_before: Optional[float]
    p_up_after: Optional[float]
    p_down_after: Optional[float]
    observations_general: str = ""

class PhotoMeta(BaseModel):
    checklist_id: int
    label: str = ""
    file_path: str
    caption: str = ""
    include_in_report: bool = True
    display_order: int = 1
