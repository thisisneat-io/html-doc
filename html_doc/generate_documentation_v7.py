#!/usr/bin/env python3
"""
NEAT YAML Documentation Generator v6
=====================================

Industry-domain-oriented documentation with UML-style ER diagrams.

Features:
1. Industry-domain categorization (ISO 14224, CFIHOS, OSDU, SAP APM)
2. Model-specific ER diagrams reflecting each model's unique content
3. Domain tags showing industry standard references
4. UML class diagram notation with proper styling
5. Multi-level abstraction (high-level → detailed)
6. Progressive detail through diagram hierarchy

Standards Referenced:
- ISO 14224: Equipment reliability and maintenance taxonomy
- CFIHOS: Capital Facilities Information Handover Specification
- OSDU: Open Subsurface Data Universe
- SAP APM: Asset Performance Management
- ISO 15288: Systems engineering lifecycle

Usage:
    python generate_documentation_v6.py <data_model.yaml> [--cdm <cognite_core.yaml>]
"""

import re
import os
import sys
import argparse
from collections import defaultdict
from pathlib import Path

# Configure stdout for UTF-8 on Windows
# reconfigure only available on real file streams, not Jupyter OutStream
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# =============================================================================
# INDUSTRY DOMAIN CATEGORIES
# Based on ISO 14224, CFIHOS, OSDU, SAP APM, ISO 15288
# =============================================================================

DOMAIN_CATEGORIES = {
    'location_geography': {
        'display_name': 'Location & Geography',
        'icon': '🌍',
        'description': 'Physical locations, sites, facilities, and spatial organization',
        'industry_standard': 'CFIHOS Physical Hierarchy',
        # Note: 'unit' removed - too generic, matches VaporRecoveryUnit etc.
        # Use 'process unit', 'orgunit' etc. for specific matches
        'patterns': ['site', 'plant', 'facility', 'area', 'country', 'location', 
                     'platform', 'warehouse', 'block', 'lease', 'process unit', 'orgunit', 'orgsubunit'],
        'cfihos_codes': ['CFIHOS_00000001', 'CFIHOS_00000002', 'CFIHOS_00000003', 'CFIHOS_00000039'],
    },
    'wells_completions': {
        'display_name': 'Wells & Completions',
        'icon': '🛢️',
        'description': 'Wells, wellbores, completions, and artificial lift systems',
        'industry_standard': 'OSDU Wells Domain',
        'patterns': ['well', 'wellbore', 'wellhead', 'completion', 'casing', 'tubing', 
                     'perforation', 'als', 'artificial lift', 'esp', 'rod pump', 'injection'],
        'property_hints': ['casingId', 'casingOd', 'wellType', 'wellStatus', 'spudDate', 
                           'completionDate', 'tvd', 'trajectory'],
    },
    'subsurface_reservoir': {
        'display_name': 'Subsurface & Reservoir',
        'icon': '🏔️',
        'description': 'Fields, structures, reservoirs, formations, and geological concepts',
        'industry_standard': 'OSDU Reservoir Domain',
        'patterns': ['reservoir', 'field', 'formation', 'zone', 'structure', 'horizon',
                     'pattern', 'play', 'prospect', 'seismic', 'substructure', 'subreservoir'],
    },
    'rotating_equipment': {
        'display_name': 'Rotating Equipment',
        'icon': '🔄',
        'description': 'Pumps, compressors, turbines, motors, and generators',
        'industry_standard': 'ISO 14224 Rotating',
        'patterns': ['pump', 'compressor', 'turbine', 'motor', 'fan', 'blower', 
                     'engine', 'generator', 'centrifugal'],
        'cfihos_codes': ['TCFIHOS_30000550', 'TCFIHOS_30000521'],
    },
    'static_equipment': {
        'display_name': 'Static Equipment',
        'icon': '⚗️',
        'description': 'Vessels, tanks, separators, exchangers, and filters',
        'industry_standard': 'ISO 14224 Static',
        'patterns': ['vessel', 'tank', 'separator', 'exchanger', 'heater', 'cooler',
                     'column', 'reactor', 'filter', 'drum', 'decanter', 'flotation', 'pond',
                     'vapor recovery', 'vru', 'scrubber', 'knockout'],
        'cfihos_codes': ['TCFIHOS_30000594', 'TCFIHOS_30000698', 'TCFIHOS_30000390'],
    },
    'piping_valves': {
        'display_name': 'Piping & Valves',
        'icon': '🔧',
        'description': 'Valves, pipes, manifolds, and flow control',
        'industry_standard': 'CFIHOS Piping Components',
        'patterns': ['valve', 'pipe', 'manifold', 'line', 'flange', 'fitting', 'skid'],
    },
    'electrical_equipment': {
        'display_name': 'Electrical Equipment',
        'icon': '⚡',
        'description': 'Transformers, switchgear, drives, and power systems',
        'industry_standard': 'ISO 14224 Electrical',
        'patterns': ['transformer', 'switchgear', 'vsd', 'vfd', 'ups', 'battery', 
                     'charger', 'cable', 'bus', 'mcc', 'breaker', 'electric',
                     'batterycharger', 'battery charger', 'rectifier', 'inverter'],
    },
    'instrumentation_control': {
        'display_name': 'Instrumentation & Control',
        'icon': '📊',
        'description': 'Instruments, sensors, meters, and control devices',
        'industry_standard': 'ISO 14224 I&C',
        'patterns': ['instrument', 'transmitter', 'sensor', 'gauge', 'meter', 'analyzer',
                     'detector', 'element', 'plc', 'dcs', 'controller', 'actuator'],
        'cfihos_codes': ['TCFIHOS_30000098', 'TCFIHOS_30000665', 'TCFIHOS_30000661', 
                         'TCFIHOS_30000674', 'TCFIHOS_30000673'],
    },
    'tags_functional_locations': {
        'display_name': 'Tags & Functional Locations',
        'icon': '🏷️',
        'description': 'Operational tags and functional location references',
        'industry_standard': 'CFIHOS Tag / SAP FLOC',
        'patterns': ['tag', 'timetag', 'functional location', 'floc'],
        'cfihos_codes': ['CFIHOS_00000028', 'CFIHOS_00000034', 'CFIHOS_00000090'],
    },
    'timeseries_measurements': {
        'display_name': 'Time Series & Measurements',
        'icon': '📈',
        'description': 'Sensor data, measurements, and forecasts',
        'industry_standard': 'Cognite CDM TimeSeries',
        'patterns': ['timeseries', 'time series', 'measurement', 'forecast', 
                     'signal', 'lowfreq', 'highfreq', 'dataframe'],
        'cdm_implements': ['CogniteTimeSeries'],
    },
    'activities_work': {
        'display_name': 'Activities & Work Management',
        'icon': '📋',
        'description': 'Maintenance, inspections, events, and work orders',
        'industry_standard': 'SAP APM / ISO 14224',
        'patterns': ['activity', 'work order', 'maintenance', 'inspection', 'event',
                     'operation', 'task', 'alert', 'notification'],
        'cdm_implements': ['CogniteActivity'],
        'cfihos_codes': ['CFIHOS_00000006', 'CFIHOS_00000007', 'EPC_00010015'],
    },
    'documents_files': {
        'display_name': 'Documents & Files',
        'icon': '📄',
        'description': 'Engineering documents, drawings, and file references',
        'industry_standard': 'CFIHOS Document / ISO 15288',
        'patterns': ['document', 'file', 'drawing', 'datasheet', 'specification', 
                     'report', 'certificate', 'transmittal'],
        'cdm_implements': ['CogniteFile'],
        'cfihos_codes': ['CFIHOS_00000022', 'CFIHOS_00000027', 'CFIHOS_00000032'],
    },
    'commercial_procurement': {
        'display_name': 'Commercial & Procurement',
        'icon': '💼',
        'description': 'Purchase orders, contracts, suppliers, and leases',
        'industry_standard': 'CFIHOS Procurement',
        'patterns': ['purchase', 'supplier', 'vendor', 'manufacturer', 'contract',
                     'lease', 'association', 'company', 'order'],
        'cfihos_codes': ['CFIHOS_00000036', 'CFIHOS_00000105'],
    },
    'epc_project': {
        'display_name': 'EPC Project',
        'icon': '🏗️',
        'description': 'Construction, commissioning, and project management',
        'industry_standard': 'CFIHOS EPC / ISO 15288',
        'patterns': ['punch', 'commissioning', 'construction', 'engineering',
                     'handover', 'package', 'assembly'],
        'cfihos_codes': ['EPC_00010011', 'EPC_00010012', 'EPC_00010025', 'EPC_00010026'],
    },
    'reference_classification': {
        'display_name': 'Reference Data & Classification',
        'icon': '📚',
        'description': 'Type codes, categories, and classification hierarchies',
        'industry_standard': 'CFIHOS RDL',
        'patterns': ['type', 'class', 'category', 'code', 'unit', 'picklist', 
                     'status', 'classification', 'discipline', 'format'],
        'cfihos_codes': ['CFIHOS_00000073', 'CFIHOS_00000075', 'CFIHOS_00000019'],
    },
    'organizational': {
        'display_name': 'Organizational',
        'icon': '🏢',
        'description': 'Organizations, departments, and business units',
        'industry_standard': 'ISO 15288',
        'patterns': ['org', 'organization', 'department', 'team', 'subunit'],
    },
    '3d_spatial': {
        'display_name': '3D & Spatial',
        'icon': '🎨',
        'description': '3D models, CAD, point clouds, and visualizations',
        'industry_standard': 'Cognite CDM 3D',
        'patterns': ['3d', 'cad', 'pointcloud', 'image', 'cubemap', 'model', 'revision'],
        'cdm_implements': ['Cognite3DObject', 'Cognite3DModel', 'CogniteCADNode'],
    },
    'cdm_core': {
        'display_name': 'CDM Core Types',
        'icon': '🔷',
        'description': 'Cognite Core Data Model foundation types',
        'industry_standard': 'Cognite CDM v1',
        'patterns': [],
    },
    'cdm_features': {
        'display_name': 'CDM Feature Mixins',
        'icon': '🧩',
        'description': 'Reusable CDM feature patterns',
        'industry_standard': 'Cognite CDM v1',
        'patterns': [],
    },
    'idm_types': {
        'display_name': 'IDM Industry Types',
        'icon': '🔶',
        'description': 'Cognite Industrial Data Model (cdf_idm) standard industry types',
        'industry_standard': 'Cognite IDM v1',
        'patterns': [],
    },
    'model_extensions': {
        'display_name': 'Model Extensions',
        'icon': '🔌',
        'description': 'Base extension types (XAsset, XEquipment, etc.)',
        'industry_standard': 'Domain Extension Pattern',
        'patterns': [],
    },
}

# CFIHOS code to domain mapping
CFIHOS_DOMAIN_MAP = {
    # Location & Geography
    'CFIHOS_00000001': 'location_geography',  # site
    'CFIHOS_00000002': 'location_geography',  # process unit
    'CFIHOS_00000003': 'location_geography',  # area
    'CFIHOS_00000039': 'location_geography',  # ISO country
    
    # Equipment base
    'CFIHOS_00000012': 'rotating_equipment',  # equipment (default to rotating, refine by name)
    
    # Rotating Equipment
    'TCFIHOS_30000314': 'rotating_equipment',  # mechanical equipment class
    'TCFIHOS_30000550': 'rotating_equipment',  # pump
    'TCFIHOS_30000521': 'rotating_equipment',  # centrifugal pump
    
    # Static Equipment
    'TCFIHOS_30000594': 'static_equipment',  # vessel
    'TCFIHOS_30000698': 'static_equipment',  # tank
    'TCFIHOS_30000390': 'static_equipment',  # heat exchanger
    'TCFIHOS_30000752': 'static_equipment',  # shell and tube exchanger
    
    # Subsea
    'TCFIHOS_30000699': 'static_equipment',  # subsea equipment class
    'TCFIHOS_30000700': 'static_equipment',  # subsea infrastructure
    
    # Instrumentation & Control
    'TCFIHOS_30000098': 'instrumentation_control',  # instrument equipment
    'TCFIHOS_30000665': 'instrumentation_control',  # detecting element
    'TCFIHOS_30000674': 'instrumentation_control',  # temperature element
    'TCFIHOS_30000661': 'instrumentation_control',  # transmitter
    'TCFIHOS_30000673': 'instrumentation_control',  # pressure transmitter
    
    # Tags
    'CFIHOS_00000028': 'tags_functional_locations',  # tag
    'CFIHOS_00000034': 'tags_functional_locations',  # tag class
    'CFIHOS_00000090': 'tags_functional_locations',  # tag or equipment class
    
    # Documents
    'CFIHOS_00000022': 'documents_files',  # document master
    'CFIHOS_00000027': 'documents_files',  # discipline document type
    'CFIHOS_00000032': 'documents_files',  # document type
    'CFIHOS_00000043': 'documents_files',  # document status
    'CFIHOS_00000054': 'documents_files',  # document type classification
    'CFIHOS_00000058': 'documents_files',  # document format
    'CFIHOS_00000024': 'documents_files',  # transmittal
    
    # EPC Project
    'EPC_00010011': 'epc_project',  # punch item
    'EPC_00010012': 'epc_project',  # commissioning item
    'EPC_00010016': 'epc_project',  # commissioning test
    'EPC_00010015': 'activities_work',  # work order
    'EPC_00010021': 'epc_project',  # control object
    'EPC_00010025': 'epc_project',  # construction node
    'EPC_00010026': 'epc_project',  # construction object
    'EPC_00010009': 'epc_project',  # engineering package
    'EPC_00010030': 'tags_functional_locations',  # tag extended
    
    # Commercial
    'CFIHOS_00000036': 'commercial_procurement',  # purchase order
    'CFIHOS_00000105': 'commercial_procurement',  # purchase order item
    'CFIHOS_00000045': 'commercial_procurement',  # export control classification
    
    # Maintenance
    'CFIHOS_00000006': 'activities_work',  # maintenance unit
    'CFIHOS_00000007': 'activities_work',  # maintenance system
    'CFIHOS_00000037': 'activities_work',  # leaf node commissioning unit
    
    # Reference Data
    'CFIHOS_00000073': 'reference_classification',  # unit of measure
    'CFIHOS_00000075': 'reference_classification',  # measurement system
    'CFIHOS_00000088': 'reference_classification',  # storage media
    'CFIHOS_00000019': 'reference_classification',  # property picklist
    'CFIHOS_00000020': 'reference_classification',  # property picklist value
    'CFIHOS_00000056': 'reference_classification',  # asset type
    'CFIHOS_00000040': 'reference_classification',  # engineering status
    'CFIHOS_00000060': 'reference_classification',  # document review type
    'CFIHOS_00000008': 'reference_classification',  # model part
    
    # Function areas
    'EPC_00010006': 'reference_classification',  # function code
    'EPC_00010007': 'reference_classification',  # category code
    'EPC_00010008': 'reference_classification',  # index type
    'EPC_00010020': 'location_geography',  # area line
    'EPC_00010022': 'location_geography',  # discipline area
    'EPC_00010023': 'location_geography',  # function area
}


def classify_by_industry_domain(view_id, view_info, all_views):
    """
    Classify a view into an industry domain category.
    
    Priority:
    1. CFIHOS/EPC/TCFIHOS code mapping (highest confidence)
    2. CDM Core/Feature types
    3. X-type extensions
    4. CDM base type + name pattern (equipment-specific classification)
    5. Name pattern matching
    6. Fallback by CDM base type
    """
    
    # Phase 1: CFIHOS/EPC/TCFIHOS code mapping
    for code, domain in CFIHOS_DOMAIN_MAP.items():
        if view_id.startswith(code) or view_id == code:
            return domain, 'cfihos_code'
    
    # Phase 2: CDM Core/Feature detection
    if view_id.startswith('Cognite'):
        if any(x in view_id for x in ['Describable', 'Sourceable', 'Visualizable', 'Schedulable']):
            return 'cdm_features', 'cdm_feature'
        if any(x in view_id for x in ['3D', 'CAD', 'PointCloud', '360', 'CubeMap', 'Image', 'Annotation', 'Diagram', 'Revision']):
            return '3d_spatial', 'cdm_3d'
        return 'cdm_core', 'cdm_core'

    # Phase 2b: IDM Industry Types (cdf_idm space)
    if view_id.startswith('cdf_idm:'):
        return 'idm_types', 'idm_type'
    
    # Phase 3: X-type extensions
    if view_id.startswith('X') and len(view_id) > 1 and view_id[1].isupper():
        return 'model_extensions', 'x_extension'
    
    # Phase 4: Check CDM base type EARLY for equipment classification
    base = get_cdm_base_type(view_id, all_views, {})
    name_lower = view_id.lower()
    display_name = (view_info.get('display_name') or view_info.get('name', '')).lower()
    combined = f"{name_lower} {display_name}"
    
    # If it's equipment, use equipment-specific pattern matching
    if base == 'CogniteEquipment':
        # Check for electrical equipment patterns first
        electrical_patterns = ['transformer', 'switchgear', 'vsd', 'vfd', 'ups', 'battery', 
                               'charger', 'cable', 'bus', 'mcc', 'breaker', 'electric',
                               'batterycharger', 'rectifier', 'inverter']
        if any(p in combined for p in electrical_patterns):
            return 'electrical_equipment', 'equipment_pattern'
        
        # Check for static equipment patterns
        static_patterns = ['vessel', 'tank', 'separator', 'exchanger', 'heater', 'cooler',
                           'column', 'reactor', 'filter', 'drum', 'decanter', 'flotation', 'pond',
                           'vapor', 'vru', 'scrubber', 'knockout', 'recovery']
        if any(p in combined for p in static_patterns):
            return 'static_equipment', 'equipment_pattern'
        
        # Check for instrumentation patterns
        instr_patterns = ['instrument', 'transmitter', 'sensor', 'gauge', 'meter', 'analyzer',
                          'detector', 'element', 'plc', 'dcs', 'controller', 'actuator']
        if any(p in combined for p in instr_patterns):
            return 'instrumentation_control', 'equipment_pattern'
        
        # Check for piping/valve patterns
        piping_patterns = ['valve', 'pipe', 'manifold', 'line', 'flange', 'fitting', 'skid']
        if any(p in combined for p in piping_patterns):
            return 'piping_valves', 'equipment_pattern'
        
        # Default equipment to rotating (pumps, compressors, motors, generators, etc.)
        return 'rotating_equipment', 'equipment_default'
    
    # Phase 5: CDM Implementation chain for non-equipment types
    implements = view_info.get('implements', '')
    for impl in implements.split(','):
        impl = impl.strip().replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
        if impl == 'CogniteTimeSeries':
            return 'timeseries_measurements', 'cdm_implements'
        if impl == 'CogniteActivity':
            return 'activities_work', 'cdm_implements'
        if impl == 'CogniteFile':
            return 'documents_files', 'cdm_implements'
    
    # Phase 6: Name pattern matching for assets and other types
    # Check domains in priority order (more specific first)
    pattern_priority = [
        'wells_completions',      # Wells before locations
        'subsurface_reservoir',   # Subsurface before locations
        'rotating_equipment',
        'static_equipment',
        'electrical_equipment',
        'instrumentation_control',
        'piping_valves',
        'tags_functional_locations',
        'timeseries_measurements',
        'activities_work',
        'documents_files',
        'commercial_procurement',
        'epc_project',
        'organizational',
        'location_geography',     # Location last (most generic for assets)
        'reference_classification',
    ]
    
    for domain_id in pattern_priority:
        domain_info = DOMAIN_CATEGORIES.get(domain_id, {})
        patterns = domain_info.get('patterns', [])
        for pattern in patterns:
            # Use word boundary for multi-word patterns, substring for single words
            if ' ' in pattern:
                if pattern in combined:
                    return domain_id, 'pattern_match'
            else:
                if re.search(rf'\b{re.escape(pattern)}\b', combined, re.IGNORECASE):
                    return domain_id, 'pattern_match'
    
    # Phase 7: Fallback by CDM base type
    if base == 'CogniteAsset':
        # Check if it's actually a location-type asset
        loc_patterns = ['site', 'plant', 'facility', 'area', 'country', 'location', 
                        'platform', 'warehouse', 'block', 'lease', 'field']
        if any(p in combined for p in loc_patterns):
            return 'location_geography', 'cdm_base'
        # Generic asset - could be many things, default to reference
        return 'reference_classification', 'cdm_base_asset'
    if base == 'CogniteTimeSeries':
        return 'timeseries_measurements', 'cdm_base'
    if base == 'CogniteActivity':
        return 'activities_work', 'cdm_base'
    if base == 'CogniteFile':
        return 'documents_files', 'cdm_base'
    
    # Phase 8: Final fallback
    if any(x in combined for x in ['type', 'class', 'code', 'status']):
        return 'reference_classification', 'fallback'
    
    return 'reference_classification', 'fallback'


# =============================================================================
# YAML PARSING
# =============================================================================

def parse_yaml_file(filepath):
    """Parse NEAT YAML file extracting all metadata, properties, views, and relationships."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    metadata = {}
    properties_by_view = defaultdict(list)
    views = {}
    direct_relations = []
    
    # Parse metadata — handles both flat "key: value" and NEAT list "- Key: k\n  Value: v"
    meta_match = re.search(r'^(.*?)(?=Properties:)', content, re.DOTALL)
    if meta_match:
        meta_content = meta_match.group(1)
        lines = meta_content.split('\n')
        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith('- Key:'):
                key = stripped[len('- Key:'):].strip()
                if i + 1 < len(lines):
                    next_stripped = lines[i + 1].strip()
                    if next_stripped.startswith('Value:'):
                        value = next_stripped[len('Value:'):].strip()
                        if key and value:
                            metadata[key] = value
                        i += 2
                        continue
            elif ':' in stripped and not stripped.startswith('-'):
                key, _, value = stripped.partition(':')
                key = key.strip()
                value = value.strip()
                if key and value:
                    metadata[key] = value
            i += 1
    
    # Parse Properties
    props_match = re.search(r'Properties:\n(.*?)(?=\nViews:|\nContainers:|\Z)', content, re.DOTALL)
    if props_match:
        props_content = props_match.group(1)
        prop_blocks = re.split(r'\n?- View:', props_content)
        
        for block in prop_blocks:
            if not block.strip():
                continue
            lines = block.strip().split('\n')
            view_name = lines[0].strip()
            
            prop_info = {'view': view_name}
            container = None
            for line in lines[1:]:
                if line.startswith('- View:'):
                    break
                if ':' in line:
                    key, _, value = line.partition(':')
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'View Property':
                        prop_info['name'] = value  # View Property externalId
                    elif key == 'Name':
                        prop_info['display_name'] = value  # View Property Name
                    elif key == 'Description':
                        prop_info['description'] = value
                    elif key == 'Value Type':
                        prop_info['type'] = value
                    elif key == 'Connection':
                        prop_info['connection'] = value
                    elif key == 'Min Count':
                        prop_info['min_count'] = value
                    elif key == 'Max Count':
                        prop_info['max_count'] = value
                    elif key == 'Container':
                        container = value.replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
                        prop_info['container'] = container  # Container reference
                    elif key == 'Container Property':
                        prop_info['container_property'] = value  # Container Property externalId
                    elif key == 'Container Property Name':
                        prop_info['container_property_name'] = value  # Container Property Name
            
            if 'name' in prop_info:
                normalized_view = view_name.replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
                prop_info['true_source'] = container if container else normalized_view
                properties_by_view[view_name].append(prop_info.copy())
                
                # Capture direct relation
                if prop_info.get('connection') and 'direct' in prop_info.get('connection', '').lower():
                    target = prop_info.get('type', '').replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
                    if target:
                        direct_relations.append({
                            'source': normalized_view,
                            'property': prop_info.get('name', ''),
                            'display_name': prop_info.get('display_name', ''),
                            'target': target,
                            'min_count': prop_info.get('min_count', '0'),
                            'max_count': prop_info.get('max_count', '1'),
                        })
    
    # Parse Views
    views_match = re.search(r'Views:\n(.*?)(?=\nContainers:|\Z)', content, re.DOTALL)
    if views_match:
        views_content = views_match.group(1)
        view_blocks = re.split(r'\n?- View: ', views_content)
        
        for block in view_blocks:
            if not block.strip():
                continue
            lines = block.strip().split('\n')
            view_name = lines[0].strip()
            
            view_info = {'name': view_name, 'implements': '', 'description': ''}
            for line in lines[1:]:
                if line.startswith('- View:'):
                    break
                if ':' in line:
                    key, _, value = line.partition(':')
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'Name':
                        view_info['display_name'] = value
                    elif key == 'Description':
                        view_info['description'] = value
                    elif key == 'Implements':
                        view_info['implements'] = value
            
            normalized = view_name.replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
            view_info['properties'] = properties_by_view.get(view_name, [])
            views[normalized] = view_info
    
    return metadata, properties_by_view, views, direct_relations


def parse_excel_file(filepath):
    """Parse NEAT Excel file (.xlsx) extracting metadata, properties, views, and relationships.

    Expects the standard NEAT Excel layout:
      Metadata  – two-column key/value rows (space, externalId, version, name, description …)
      Properties – row 1: section title, row 2: column headers, row 3+: data
      Views      – same layout as Properties

    Applies the same in-memory cleaning that clean_and_convert_pidm.py performs so that
    non-compliant sheets (spaces in property IDs, duplicate rows, missing container
    harmonization, undefined CFIHOS view placeholders) are handled gracefully.
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError(
            "openpyxl is required to read Excel files.  "
            "Install it with:  pip install openpyxl"
        )

    wb = openpyxl.load_workbook(filepath, data_only=True)

    metadata = {}
    properties_by_view = defaultdict(list)
    views = {}
    direct_relations = []

    # ── Helper ───────────────────────────────────────────────────────────────
    def _cell(row, col_map, key, default=''):
        """Return the string value of a named column in a row, or *default*."""
        idx = col_map.get(key)
        if idx is None or idx >= len(row):
            return default
        v = row[idx]
        if v is None:
            return default
        s = str(v).strip()
        return default if s.lower() in ('none', 'null') else s

    def _num(row, col_map, key, default='0'):
        idx = col_map.get(key)
        if idx is None or idx >= len(row):
            return default
        v = row[idx]
        if isinstance(v, (int, float)):
            return str(int(v))
        s = str(v).strip() if v is not None else ''
        return s if s and s.lower() not in ('none', 'null') else default

    # ── Metadata ─────────────────────────────────────────────────────────────
    if 'Metadata' in wb.sheetnames:
        for row in wb['Metadata'].iter_rows(values_only=True):
            if row[0] is not None and len(row) >= 2 and row[1] is not None:
                metadata[str(row[0]).strip()] = str(row[1]).strip()

    # ── Properties (with in-memory cleaning) ─────────────────────────────────
    if 'Properties' in wb.sheetnames:
        all_rows = list(wb['Properties'].iter_rows(values_only=True))
        # Row 0 = section title, Row 1 = column headers
        if len(all_rows) >= 2:
            col = {
                str(h).strip(): i
                for i, h in enumerate(all_rows[1])
                if h is not None
            }
            # Convert to mutable lists for in-place cleaning
            data_rows = [list(r) for r in all_rows[2:]]

            # Known rename map for specific invalid property IDs (from clean_and_convert_pidm.py)
            _rename_map = {
                'Involves Activities': 'involvesActivities',
                'maintenance order': 'maintenanceOrder',
                'revision files': 'revisionFiles',
                'sas properties': 'sasProperties',
                'time series': 'timeSeries',
                'work order revision': 'workOrderRevision',
                'work order': 'workOrder',
            }
            vp_idx = col.get('View Property')

            # ── Clean 1: Fix spaces in View Property IDs ──────────────────
            if vp_idx is not None:
                for row in data_rows:
                    if vp_idx < len(row) and isinstance(row[vp_idx], str):
                        val = row[vp_idx].strip()
                        if val in _rename_map:
                            row[vp_idx] = _rename_map[val]
                        elif ' ' in val:
                            row[vp_idx] = '_'.join(val.split())

            # ── Clean 2: Harmonize container property columns ─────────────
            # For each (Container, Container Property) group, fill nulls from
            # the first row in the group that has a non-null value.
            _harmonize_cols = [
                'Auto Increment', 'Connection', 'Constraint',
                'Container Property Description', 'Container Property Name',
                'Default', 'Index', 'Max Count', 'Min Count', 'Value Type',
            ]
            c_idx  = col.get('Container')
            cp_idx = col.get('Container Property')
            if c_idx is not None and cp_idx is not None:
                grouped = defaultdict(list)
                for i, row in enumerate(data_rows):
                    c_val  = row[c_idx]  if c_idx  < len(row) else None
                    cp_val = row[cp_idx] if cp_idx < len(row) else None
                    if isinstance(c_val, str) and c_val.strip() \
                            and isinstance(cp_val, str) and cp_val.strip():
                        grouped[(c_val.strip(), cp_val.strip())].append(i)

                for _, indices in grouped.items():
                    if len(indices) < 2:
                        continue
                    for hcol in _harmonize_cols:
                        hcol_idx = col.get(hcol)
                        if hcol_idx is None:
                            continue
                        canonical = None
                        for i in indices:
                            v = data_rows[i][hcol_idx] if hcol_idx < len(data_rows[i]) else None
                            if v is not None and str(v).strip() not in ('', 'None', 'null'):
                                canonical = v
                                break
                        if canonical is not None:
                            for i in indices:
                                if hcol_idx < len(data_rows[i]):
                                    data_rows[i][hcol_idx] = canonical

            # ── Clean 3: Deduplicate (View, View Property) rows ───────────
            v_idx  = col.get('View', 0)
            seen_pairs = set()
            deduped = []
            for row in data_rows:
                view_val = row[v_idx]  if v_idx  < len(row) else None
                prop_val = row[vp_idx] if vp_idx is not None and vp_idx < len(row) else None
                key = (
                    str(view_val).strip() if view_val is not None else '',
                    str(prop_val).strip() if prop_val  is not None else '',
                )
                if key == ('', ''):
                    continue
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                deduped.append(row)
            data_rows = deduped

            # ── Parse cleaned rows into data structures ───────────────────
            for row in data_rows:
                view_name = _cell(row, col, 'View')
                if not view_name:
                    continue
                prop_id = _cell(row, col, 'View Property')
                if not prop_id:
                    continue

                container_raw = _cell(row, col, 'Container')
                container = (
                    container_raw
                    .replace('cdf_cdm:', '')
                    .replace('(version=v1)', '')
                    .strip()
                )
                normalized_view = (
                    view_name
                    .replace('cdf_cdm:', '')
                    .replace('(version=v1)', '')
                    .strip()
                )
                connection_val = _cell(row, col, 'Connection')

                prop_info = {
                    'view': view_name,
                    'name': prop_id,
                    'display_name': _cell(row, col, 'Name'),
                    'description': _cell(row, col, 'Description'),
                    'connection': connection_val,
                    'type': _cell(row, col, 'Value Type'),
                    'min_count': _num(row, col, 'Min Count', '0'),
                    'max_count': _num(row, col, 'Max Count', '1'),
                    'container': container,
                    'container_property': _cell(row, col, 'Container Property'),
                    'container_property_name': _cell(row, col, 'Container Property Name'),
                    'true_source': container if container else normalized_view,
                }
                properties_by_view[view_name].append(prop_info)

                # Capture direct relation
                if connection_val and 'direct' in connection_val.lower():
                    target = (
                        prop_info['type']
                        .replace('cdf_cdm:', '')
                        .replace('(version=v1)', '')
                        .strip()
                    )
                    if target:
                        direct_relations.append({
                            'source': normalized_view,
                            'property': prop_id,
                            'display_name': prop_info['display_name'],
                            'target': target,
                            'min_count': prop_info['min_count'],
                            'max_count': prop_info['max_count'],
                        })

    # ── Views ────────────────────────────────────────────────────────────────
    if 'Views' in wb.sheetnames:
        all_rows = list(wb['Views'].iter_rows(values_only=True))
        if len(all_rows) >= 2:
            col = {
                str(h).strip(): i
                for i, h in enumerate(all_rows[1])
                if h is not None
            }
            existing_view_names = set()
            for row in all_rows[2:]:
                view_name = _cell(row, col, 'View')
                if not view_name:
                    continue
                existing_view_names.add(view_name)
                normalized = (
                    view_name
                    .replace('cdf_cdm:', '')
                    .replace('(version=v1)', '')
                    .strip()
                )
                view_info = {
                    'name': view_name,
                    'display_name': _cell(row, col, 'Name'),
                    'description': _cell(row, col, 'Description'),
                    'implements': _cell(row, col, 'Implements'),
                    'properties': properties_by_view.get(view_name, []),
                }
                views[normalized] = view_info

            # ── Clean 4: Add placeholder views for CFIHOS_ value-type refs ─
            # Any CFIHOS_XXXXXXX used as a relation target but absent from
            # the Views sheet becomes an empty stub so diagrams can reference it.
            for props in properties_by_view.values():
                for p in props:
                    vtype = p.get('type', '')
                    if not vtype:
                        continue
                    # strip namespace prefix / version suffix
                    ref = re.sub(r'\(version=.*?\)', '', vtype).split(':')[-1].strip()
                    if ref.startswith('CFIHOS_') and ref not in existing_view_names:
                        existing_view_names.add(ref)
                        views[ref] = {
                            'name': ref,
                            'display_name': '',
                            'description': '',
                            'implements': '',
                            'properties': [],
                        }

    return metadata, properties_by_view, views, direct_relations


def get_inheritance_depth(view_id, all_views, cache=None):
    """Calculate inheritance depth for a view."""
    if cache is None:
        cache = {}
    if view_id in cache:
        return cache[view_id]
    
    normalized = view_id.replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
    view = all_views.get(normalized)
    
    if not view:
        cache[view_id] = 0
        return 0
    
    implements = view.get('implements', '')
    if not implements:
        cache[view_id] = 0
        return 0
    
    max_depth = 0
    for parent in implements.split(','):
        parent = parent.strip().replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
        if parent and parent in all_views:
            depth = get_inheritance_depth(parent, all_views, cache)
            max_depth = max(max_depth, depth + 1)
    
    cache[view_id] = max_depth
    return max_depth


def get_all_properties_for_view(view_id, properties_by_view, all_views):
    """Get all properties for a view including inherited ones."""
    normalized = view_id.replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
    
    own_props = []
    for key in [view_id, f'cdf_cdm:{normalized}(version=v1)', normalized]:
        if key in properties_by_view:
            own_props = list(properties_by_view[key])
            break
    
    for prop in own_props:
        true_source = prop.get('true_source', normalized)
        if true_source != normalized:
            prop['inherited_from'] = true_source
        else:
            prop['inherited_from'] = None
    
    view = all_views.get(normalized, {})
    implements = view.get('implements', '')
    
    if implements:
        inherited = set(p.get('name') for p in own_props)
        
        for parent in implements.split(','):
            parent = parent.strip().replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
            if not parent:
                continue
            
            parent_props = get_all_properties_for_view(parent, properties_by_view, all_views)
            
            for prop in parent_props:
                if prop.get('name') not in inherited:
                    inherited.add(prop.get('name'))
                    new_prop = prop.copy()
                    source = prop.get('inherited_from') or prop.get('true_source') or parent
                    new_prop['inherited_from'] = source
                    own_props.append(new_prop)
    
    return own_props


def build_inheritance_tree(views):
    """Build complete inheritance tree."""
    children = defaultdict(list)
    parents = defaultdict(list)
    
    for view_id, info in views.items():
        impl = info.get('implements', '')
        if impl:
            parent_list = [p.strip().replace('cdf_cdm:', '').replace('(version=v1)', '').strip() 
                          for p in impl.split(',')]
            for parent in parent_list:
                if parent:
                    children[parent].append(view_id)
                    parents[view_id].append(parent)
    
    return children, parents


def get_cdm_base_type(view_id, all_views, cache=None):
    """Recursively find the CDM base type."""
    if cache is None:
        cache = {}
    if view_id in cache:
        return cache[view_id]
    
    if view_id.startswith('Cognite'):
        cache[view_id] = view_id
        clean = view_id.replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
        return clean
    
    view = all_views.get(view_id, {})
    implements = view.get('implements', '')
    
    if not implements:
        cache[view_id] = None
        return None
    
    for parent in implements.split(','):
        parent = parent.strip().replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
        if parent.startswith('Cognite'):
            cache[view_id] = parent
            return parent
        if parent in all_views:
            base = get_cdm_base_type(parent, all_views, cache)
            if base:
                cache[view_id] = base
                return base
    
    cache[view_id] = None
    return None


# =============================================================================
# CATEGORIZATION
# =============================================================================

def categorize_by_industry_domain(views, all_views):
    """Categorize views by industry domain using multi-phase classification."""
    categories = defaultdict(list)
    view_domains = {}  # Track domain info for each view
    
    for view_id, view_info in views.items():
        domain, method = classify_by_industry_domain(view_id, view_info, all_views)
        categories[domain].append(view_id)
        view_domains[view_id] = {
            'domain': domain,
            'classification_method': method,
            'industry_standard': DOMAIN_CATEGORIES.get(domain, {}).get('industry_standard', ''),
        }
    
    # Build category labels from DOMAIN_CATEGORIES
    category_labels = {}
    for domain_id, domain_info in DOMAIN_CATEGORIES.items():
        if domain_id in categories and categories[domain_id]:
            category_labels[domain_id] = (
                domain_info['icon'],
                domain_info['display_name'],
                domain_info['description']
            )
    
    # Sort views within each category
    for cat_name in categories:
        categories[cat_name].sort()
    
    return dict(categories), category_labels, view_domains


def categorize_by_cdm_hierarchy(views, all_views):
    """Backward-compatible wrapper - now uses industry domain categorization."""
    categories, category_labels, view_domains = categorize_by_industry_domain(views, all_views)
    return categories, category_labels


# =============================================================================
# UML-STYLE ER DIAGRAM GENERATION
# Multi-level abstraction with topic focus
# =============================================================================

class UMLDiagramGenerator:
    """Generates domain-model-centric UML ER diagrams.
    
    Domain views (from the model's own Views list) are the heroes of all diagrams.
    CDM views (CogniteDescribable, CogniteAsset, etc.) play a supporting contextual role.
    """
    
    def __init__(self, views, all_views, direct_relations, model_name, domain_view_ids=None):
        self.views = views
        self.all_views = all_views
        self.relations = direct_relations
        self.model_name = model_name
        self.children, self.parents = build_inheritance_tree(views)
        
        self.relations_by_source = defaultdict(list)
        self.relations_by_target = defaultdict(list)
        for rel in direct_relations:
            self.relations_by_source[rel['source']].append(rel)
            self.relations_by_target[rel['target']].append(rel)
        
        self.node_mapping = {}
        
        self._init_domain_views(domain_view_ids)
        self._detect_clusters()
    
    def _init_domain_views(self, domain_view_ids):
        """Separate domain views from CDM views."""
        self.domain_views = {}
        self.cdm_views = {}
        domain_ids = domain_view_ids or set()
        
        for vid, vinfo in self.views.items():
            if domain_ids:
                if vid in domain_ids:
                    self.domain_views[vid] = vinfo
                else:
                    self.cdm_views[vid] = vinfo
            else:
                if not vid.startswith('Cognite') and not vid.startswith('cdf_cdm:'):
                    self.domain_views[vid] = vinfo
                else:
                    self.cdm_views[vid] = vinfo
    
    def _detect_clusters(self):
        """Auto-detect functional clusters from naming patterns and relationships."""
        domain_ids = set(self.domain_views.keys())
        if not domain_ids:
            self.clusters = {}
            return
        
        prefix_groups = defaultdict(list)
        ungrouped = []
        
        for v in sorted(domain_ids):
            parts = v.split('_')
            if len(parts) >= 2 and parts[0] and len(parts[0]) >= 2:
                prefix_groups[parts[0]].append(v)
            else:
                ungrouped.append(v)
        
        self.clusters = {}
        used = set()
        
        for prefix, pviews in sorted(prefix_groups.items(), key=lambda x: -len(x[1])):
            if len(pviews) >= 3:
                self.clusters[f"{prefix} Classification"] = pviews
                used.update(pviews)
            else:
                ungrouped.extend(pviews)
        
        remaining = [v for v in ungrouped if v not in used]
        
        if remaining:
            adj = defaultdict(set)
            for rel in self.relations:
                src, tgt = rel['source'], rel['target']
                if src in remaining and tgt in remaining:
                    adj[src].add(tgt)
                    adj[tgt].add(src)
            
            visited = set()
            for v in remaining:
                if v not in visited:
                    component = []
                    queue = [v]
                    while queue:
                        node = queue.pop(0)
                        if node in visited:
                            continue
                        visited.add(node)
                        component.append(node)
                        for neighbor in adj.get(node, []):
                            if neighbor not in visited:
                                queue.append(neighbor)
                    
                    if component:
                        hub = max(component, key=lambda x: len(adj.get(x, set())))
                        # Name by most-common CDM parent so cluster label never matches a node label
                        from collections import Counter as _Ctr
                        parent_ctr = _Ctr(
                            p for v in component
                            for p in [self._get_cdm_parent(v)] if p
                        )
                        if parent_ctr:
                            base = parent_ctr.most_common(1)[0][0] + " Types"
                        else:
                            base = hub
                        # ensure unique key
                        key = base
                        suffix = 2
                        while key in self.clusters:
                            key = f"{base} ({suffix})"
                            suffix += 1
                        self.clusters[key] = component
        
        if not self.clusters:
            self.clusters[self.model_name] = sorted(domain_ids)
    
    def _get_cdm_parent(self, view_id):
        """Get the CDM parent type name for a domain view."""
        view = self.all_views.get(view_id, {})
        implements = view.get('implements', '')
        if implements:
            for parent in implements.split(','):
                parent = parent.strip().replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
                if parent and parent.startswith('Cognite'):
                    return parent
        return None
    
    def _get_own_properties(self, view_id):
        """Get only the view's OWN properties (not inherited from CDM containers)."""
        if view_id in self.views:
            props = self.views[view_id].get('properties', [])
            return [p for p in props if not p.get('inherited_from')]
        return []
    
    def _get_label(self, view_id):
        """Get clean display label for a view."""
        def _clean(s):
            return s.replace('cdf_cdm:', '').replace('(version=v1)', '').strip()

        if view_id in self.views:
            name = _clean(self.views[view_id].get('display_name') or self.views[view_id].get('name', ''))
            if name and name != view_id:
                return name
        elif view_id in self.all_views:
            name = _clean(self.all_views[view_id].get('display_name') or self.all_views[view_id].get('name', ''))
            if name and name != view_id:
                return name
        return view_id
    
    def _sanitize(self, s, record=True):
        """Make string safe for Mermaid IDs and record mapping."""
        sanitized = re.sub(r'[^a-zA-Z0-9]', '_', s)[:25]
        if record and (s in self.views or s in self.all_views):
            self.node_mapping[sanitized] = s
        return sanitized
    
    def _register_node(self, view_id):
        """Register a node ID for clickability, including display name mapping."""
        sanitized = re.sub(r'[^a-zA-Z0-9]', '_', view_id)[:25]
        if view_id in self.views or view_id in self.all_views:
            self.node_mapping[sanitized] = view_id
            self.node_mapping[view_id] = view_id
            label = self._get_label(view_id)
            if label and label != view_id:
                self.node_mapping[label] = view_id
    
    def _get_multiplicity(self, rel):
        """Get UML multiplicity string."""
        min_c = rel.get('min_count', '0')
        max_c = rel.get('max_count', '1')
        
        try:
            min_c = int(min_c) if min_c and min_c != 'null' else 0
            max_c = int(max_c) if max_c and max_c != 'null' else 1
        except:
            min_c, max_c = 0, 1
        
        if min_c == 0 and max_c == 1:
            return "0..1"
        elif min_c == 1 and max_c == 1:
            return "1"
        elif min_c == 0 and max_c > 1:
            return "0..*"
        elif min_c == 1 and max_c > 1:
            return "1..*"
        else:
            return f"{min_c}..{max_c}"
    
    def _create_class_diagram(self, title, description, nodes, edges, style_classes=None):
        """Create a UML class diagram HTML block."""
        if not nodes:
            return ""
        
        nodes_str = '\n    '.join(nodes)
        edges_str = '\n    '.join(edges) if edges else ''
        styles_str = '\n    '.join(style_classes) if style_classes else ''
        
        return f'''
            <div class="er-diagram-box">
                <h3>{title}</h3>
                <p class="diagram-desc">{description}</p>
                <pre class="mermaid-source">
classDiagram
    {nodes_str}
    {edges_str}
    {styles_str}
                </pre>
            </div>'''
    
    def _get_domain_relations(self, include_cdm_targets=False):
        """Get relations involving domain views.

        If include_cdm_targets is False (default), only domain→domain edges are returned
        (safe for diagrams without CDM nodes present).
        If True, also include domain→CDM edges so nothing is hidden.
        """
        domain_ids = set(self.domain_views.keys())
        result = []
        for r in self.relations:
            if r['source'] not in domain_ids:
                continue
            if r['target'] in domain_ids:
                result.append(r)
            elif include_cdm_targets and r['target'] in self.all_views:
                result.append(r)
        return result

    def _get_describable_fringe(self, domain_rels):
        """Low-connected CogniteDescribable implementers that crowd horizontal layouts."""
        degree_map = defaultdict(int)
        for rel in domain_rels:
            degree_map[rel['source']] += 1
            degree_map[rel['target']] += 1

        fringe = []
        for v in self.domain_views:
            if self._get_cdm_parent(v) == 'CogniteDescribable' and degree_map.get(v, 0) <= 1:
                fringe.append(v)
        return sorted(fringe)

    def _split_core_support_views(self, cluster_views, degree_map):
        """Split cluster into strongly connected core and weakly connected support views."""
        ordered = [v for v in cluster_views if v in self.domain_views]
        if len(ordered) <= 8:
            return ordered, []

        support = [v for v in ordered if degree_map.get(v, 0) <= 1]
        if len(support) < 3:
            return ordered, []

        core = [v for v in ordered if v not in support]
        if not core:
            # Keep at least one anchor node in core for readability.
            core = support[:1]
            support = support[1:]
        return core, support

    def _chunk_list(self, items, chunk_size):
        """Yield consecutive chunks from list."""
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]
    
    def _click_lines(self, added_views):
        """Generate Mermaid click directives for all added views that have detail cards."""
        lines = []
        for v in sorted(added_views):
            sanitized = self._sanitize(v, record=False)
            if v in self.views:
                # Use sanitized node-id as callback arg — colons in view IDs break Mermaid 11
                lines.append(f'    click {sanitized} call openModalFromDiagram("{sanitized}")')
        return lines
    
    # =========================================================================
    # LEVEL 1: DOMAIN MODEL OVERVIEW
    # =========================================================================
    
    def level1_domain_overview(self):
        """All domain views with vertical-spine layout; CDM parents as ghost nodes."""
        if len(self.domain_views) < 2:
            return ""

        lines = ['flowchart TB']
        cluster_colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']
        all_rels = self._get_domain_relations(include_cdm_targets=True)
        domain_rels = self._get_domain_relations(include_cdm_targets=False)

        # CDM parent ghost nodes (implements targets)
        cdm_parents = set()
        for v in self.domain_views:
            parent = self._get_cdm_parent(v)
            if parent:
                cdm_parents.add(parent)

        sg_lines, inv_lines, spine_anchors, added = self._build_vertical_sections(
            set(), domain_rels, cdm_ghost_nodes=cdm_parents)
        lines.extend(sg_lines)
        lines.extend(inv_lines)

        # All relation edges
        seen_edges = set()
        for rel in all_rels:
            src, tgt = rel['source'], rel['target']
            edge_key = (src, tgt)
            if src in added and tgt in added and edge_key not in seen_edges:
                seen_edges.add(edge_key)
                prop = rel.get('display_name') or rel.get('property', '')
                lines.append(f'    {self._sanitize(src)} -->|"{prop[:18]}"| {self._sanitize(tgt)}')

        for v in self.domain_views:
            parent = self._get_cdm_parent(v)
            if parent and parent in added:
                lines.append(f'    {parent} -.->|implements| {self._sanitize(v)}')

        lines.append('    classDef cdm fill:#334155,stroke:#64748b,stroke-width:1px,color:#94a3b8,stroke-dasharray:5 5')

        for idx, (_, cluster_views) in enumerate(self.clusters.items()):
            color = cluster_colors[idx % len(cluster_colors)]
            for v in cluster_views:
                lines.append(f'    style {self._sanitize(v)} fill:{color},color:#fff,stroke:#fff,stroke-width:2px')

        lines.extend(self._click_lines(added))

        return f'''
            <div class="er-diagram-box">
                <h3>Level 1: {self.model_name} - Domain Overview</h3>
                <p class="diagram-desc">All domain views grouped by function. CDM types shown as ghost context.</p>
                <pre class="mermaid-source">
{chr(10).join(lines)}
                </pre>
            </div>'''
    
    # =========================================================================
    # LEVEL 2: ENTITY RELATIONSHIP FOCUS (one diagram per domain view)
    # =========================================================================

    def level2_entity_focus(self, view_id):
        """
        Focused diagram for a single entity: the entity itself (highlighted),
        every entity it points TO (outgoing relations), every entity that points
        TO it (incoming relations), and its CDM parent as a ghost node.
        """
        focus_label = self._get_label(view_id)
        focus_s    = self._sanitize(view_id)

        outgoing_rels = self.relations_by_source.get(view_id, [])
        incoming_rels = self.relations_by_target.get(view_id, [])

        out_targets = {r['target'] for r in outgoing_rels if r['target'] != view_id}
        in_sources  = {r['source'] for r in incoming_rels if r['source'] != view_id}
        neighbours  = (out_targets | in_sources) & set(self.domain_views.keys())

        cdm_parent  = self._get_cdm_parent(view_id)

        # Skip trivially empty diagrams (single isolated node with no CDM parent)
        if not neighbours and not cdm_parent:
            return ""

        lines = ['flowchart LR']
        added = set()

        # ── Focus entity ──────────────────────────────────────────────────────
        self._register_node(view_id)
        lines.append(f'    {focus_s}["{focus_label}"]')
        added.add(view_id)

        # ── Outgoing targets ──────────────────────────────────────────────────
        out_nodes = sorted(out_targets & set(self.domain_views.keys()))
        if out_nodes:
            lines.append('    subgraph OUT["Outgoing relations"]')
            for t in out_nodes:
                s = self._sanitize(t)
                self._register_node(t)
                lines.append(f'        {s}["{self._get_label(t)}"]')
                added.add(t)
            lines.append('    end')

        # ── Incoming sources ──────────────────────────────────────────────────
        in_nodes = sorted(in_sources & set(self.domain_views.keys()))
        # exclude those already in OUT
        in_nodes = [v for v in in_nodes if v not in out_targets]
        if in_nodes:
            lines.append('    subgraph IN["Incoming relations"]')
            for s_id in in_nodes:
                s = self._sanitize(s_id)
                self._register_node(s_id)
                lines.append(f'        {s}["{self._get_label(s_id)}"]')
                added.add(s_id)
            lines.append('    end')

        # ── CDM parent ghost ──────────────────────────────────────────────────
        if cdm_parent and cdm_parent not in added:
            lines.append(f'    {cdm_parent}(["{self._get_label(cdm_parent)}"]):::cdm')
            self._register_node(cdm_parent)
            added.add(cdm_parent)

        # ── Edges ─────────────────────────────────────────────────────────────
        seen_edges = set()

        # CDM implements
        if cdm_parent and cdm_parent in added:
            lines.append(f'    {focus_s} -.->|implements| {cdm_parent}')

        # Outgoing data relations
        for rel in outgoing_rels:
            tgt = rel['target']
            if tgt in added:
                key = (view_id, tgt)
                if key not in seen_edges:
                    seen_edges.add(key)
                    prop = rel.get('display_name') or rel.get('property', '')
                    mult = self._get_multiplicity(rel)
                    lines.append(
                        f'    {focus_s} -->|"{prop[:20]} [{mult}]"| {self._sanitize(tgt)}')

        # Incoming data relations
        for rel in incoming_rels:
            src = rel['source']
            if src in added:
                key = (src, view_id)
                if key not in seen_edges:
                    seen_edges.add(key)
                    prop = rel.get('display_name') or rel.get('property', '')
                    mult = self._get_multiplicity(rel)
                    lines.append(
                        f'    {self._sanitize(src)} -->|"{prop[:20]} [{mult}]"| {focus_s}')

        # Cross-edges between neighbours (out_targets ↔ in_sources)
        for rel in self.relations:
            src, tgt = rel['source'], rel['target']
            if src in added and tgt in added and src != view_id and tgt != view_id:
                key = (src, tgt)
                if key not in seen_edges:
                    seen_edges.add(key)
                    prop = rel.get('display_name') or rel.get('property', '')
                    mult = self._get_multiplicity(rel)
                    lines.append(
                        f'    {self._sanitize(src)} -->|"{prop[:20]} [{mult}]"| {self._sanitize(tgt)}')

        # ── Styles ────────────────────────────────────────────────────────────
        lines.append('    classDef cdm fill:#1e3a5f,stroke:#3b82f6,stroke-width:1px,color:#93c5fd,stroke-dasharray:5 5')
        lines.append(f'    style {focus_s} fill:#3b82f6,color:#fff,stroke:#fff,stroke-width:3px')
        for t in out_nodes:
            lines.append(f'    style {self._sanitize(t)} fill:#10b981,color:#fff,stroke:#fff,stroke-width:2px')
        for s_id in in_nodes:
            lines.append(f'    style {self._sanitize(s_id)} fill:#f59e0b,color:#fff,stroke:#fff,stroke-width:2px')
        # views that appear in both OUT and IN: use a blended purple
        for v in (out_targets & in_sources & set(self.domain_views.keys())):
            lines.append(f'    style {self._sanitize(v)} fill:#8b5cf6,color:#fff,stroke:#fff,stroke-width:2px')

        lines.extend(self._click_lines(added))

        return f'''
            <div class="er-diagram-box">
                <h3>Level 2: {focus_label}</h3>
                <p class="diagram-desc">
                    Relations for <strong>{focus_label}</strong>.
                    <span style="color:#3b82f6">■</span> focus &nbsp;
                    <span style="color:#10b981">■</span> outgoing targets &nbsp;
                    <span style="color:#f59e0b">■</span> incoming sources &nbsp;
                    <span style="color:#8b5cf6">■</span> both directions
                </p>
                <pre class="mermaid-source">
{chr(10).join(lines)}
                </pre>
            </div>'''
    
    # =========================================================================
    # LEVEL 3: COMPLETE RELATIONSHIP MAP
    # =========================================================================

    def _build_vertical_sections(self, describable_fringe, domain_rels, cdm_ghost_nodes=None):
        """
        Build subgraph definitions + invisible-edge spine for vertical layout.

        cdm_ghost_nodes: optional set of CDM view IDs to add as a 'CDM References'
                         section so edges pointing to them can be rendered.

        Returns (subgraph_lines, invisible_lines, spine_anchors, added).
        """
        subgraph_lines = []
        invisible_lines = []
        spine_anchors = []
        added = set()

        def _add_section(section_id, section_label, view_list, indent='    ', ghost=False):
            if not view_list:
                return None
            sanitized_ids = []
            use_wrapper = len(view_list) > 1
            if use_wrapper:
                subgraph_lines.append(f'{indent}subgraph {section_id}["{section_label}"]')
            for v in view_list:
                s = self._sanitize(v)
                self._register_node(v)
                label = self._get_label(v)
                node_indent = (indent + '    ') if use_wrapper else indent
                if ghost:
                    subgraph_lines.append(f'{node_indent}{s}(["{label}"]):::cdm')
                else:
                    subgraph_lines.append(f'{node_indent}{s}["{label}"]')
                added.add(v)
                sanitized_ids.append(s)
            if use_wrapper:
                subgraph_lines.append(f'{indent}end')
            for i in range(len(sanitized_ids) - 1):
                invisible_lines.append(f'    {sanitized_ids[i]} ~~~ {sanitized_ids[i + 1]}')
            return sanitized_ids[0]

        # Fringe leaf block
        fringe_list = sorted(describable_fringe)
        anchor = _add_section('DS', 'Describable Leaf Types', fringe_list)
        if anchor:
            spine_anchors.append(anchor)

        # One subgraph per cluster (non-fringe nodes)
        for idx, (cluster_name, cluster_views) in enumerate(self.clusters.items()):
            visible = [v for v in cluster_views if v not in describable_fringe]
            if not visible:
                continue
            anchor = _add_section(f'RM{idx}', cluster_name, visible)
            if anchor:
                spine_anchors.append(anchor)

        # CDM ghost nodes (targets of domain→CDM edges not shown elsewhere)
        if cdm_ghost_nodes:
            ghost_list = sorted(cdm_ghost_nodes - set(added))
            anchor = _add_section('CDMREF', 'CDM References', ghost_list, ghost=True)
            if anchor:
                spine_anchors.append(anchor)

        # Cross-section spine
        for i in range(len(spine_anchors) - 1):
            invisible_lines.append(f'    {spine_anchors[i]} ~~~ {spine_anchors[i + 1]}')

        return subgraph_lines, invisible_lines, spine_anchors, added

    def level3_relationship_map(self):
        """Domain-only view: all domain views and their data relations, no CDM nodes."""
        if len(self.domain_views) < 2:
            return ""

        lines = ['flowchart TB']
        cluster_colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']

        # Only domain↔domain relations (no CDM targets)
        domain_rels = self._get_domain_relations(include_cdm_targets=False)
        describable_fringe = set(self._get_describable_fringe(domain_rels))

        # No CDM ghost nodes — purely domain
        sg_lines, inv_lines, _, added = self._build_vertical_sections(
            describable_fringe, domain_rels, cdm_ghost_nodes=None)
        lines.extend(sg_lines)
        lines.extend(inv_lines)

        # Data relation edges — domain to domain only
        seen_edges = set()
        for rel in domain_rels:
            src, tgt = rel['source'], rel['target']
            edge_key = (src, tgt)
            if src in added and tgt in added and edge_key not in seen_edges:
                seen_edges.add(edge_key)
                prop = rel.get('display_name') or rel.get('property', '')
                mult = self._get_multiplicity(rel)
                lines.append(f'    {self._sanitize(src)} -->|"{prop[:18]} [{mult}]"| {self._sanitize(tgt)}')

        # Cluster colour coding
        for idx, (_, cluster_views) in enumerate(self.clusters.items()):
            color = cluster_colors[idx % len(cluster_colors)]
            for v in cluster_views:
                lines.append(f'    style {self._sanitize(v)} fill:{color},color:#fff,stroke:#fff,stroke-width:2px')

        lines.extend(self._click_lines(added))

        return f'''
            <div class="er-diagram-box">
                <h3>Level 3: {self.model_name} - Domain Relationship Map</h3>
                <p class="diagram-desc">All domain views and their data relations — no CDM infrastructure shown. Pure signal about how your own entities connect. Click any view to see details.</p>
                <pre class="mermaid-source">
{chr(10).join(lines)}
                </pre>
            </div>'''
    
    # =========================================================================
    # LEVEL 4: FULL ARCHITECTURE WITH CDM CONTEXT
    # =========================================================================
    
    def level4_full_architecture(self):
        """Domain types prominent, full CDM foundation shown with all relation edges."""
        if len(self.domain_views) < 2:
            return ""

        lines = ['flowchart TB']
        cluster_colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']
        domain_rels_only = self._get_domain_relations(include_cdm_targets=False)
        all_rels = self._get_domain_relations(include_cdm_targets=True)
        describable_fringe = set(self._get_describable_fringe(domain_rels_only))

        # Domain sections chained vertically (fringe + clusters)
        sg_lines, inv_lines, spine_anchors, added = self._build_vertical_sections(
            describable_fringe, domain_rels_only)
        lines.extend(sg_lines)
        lines.extend(inv_lines)

        # Build complete CDM node set: implements-parents + direct-relation targets
        cdm_parents = set()
        for v in self.domain_views:
            parent = self._get_cdm_parent(v)
            if parent:
                cdm_parents.add(parent)
                pp_view = self.all_views.get(parent, {})
                for pp in pp_view.get('implements', '').split(','):
                    pp = pp.strip().replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
                    if pp and pp.startswith('Cognite'):
                        cdm_parents.add(pp)
        cdm_rel_targets = {r['target'] for r in all_rels if r['target'] not in set(self.domain_views.keys())}
        cdm_all = sorted(cdm_parents | cdm_rel_targets)

        if cdm_all:
            lines.append('    subgraph CDM["CDM Foundation"]')
            for cp in cdm_all:
                lines.append(f'        {cp}(["{cp}"]):::cdm')
                self._register_node(cp)
                added.add(cp)
            lines.append('    end')
            if spine_anchors:
                lines.append(f'    {spine_anchors[-1]} ~~~ {self._sanitize(cdm_all[0], record=False)}')
            for i in range(len(cdm_all) - 1):
                lines.append(f'    {self._sanitize(cdm_all[i], record=False)} ~~~ {self._sanitize(cdm_all[i + 1], record=False)}')

        # All data relation edges (domain→domain + domain→CDM)
        seen_edges = set()
        for rel in all_rels:
            src, tgt = rel['source'], rel['target']
            edge_key = (src, tgt)
            if edge_key not in seen_edges and src in added and tgt in added:
                seen_edges.add(edge_key)
                prop = rel.get('display_name') or rel.get('property', '')
                lines.append(f'    {self._sanitize(src)} -->|"{prop[:15]}"| {self._sanitize(tgt)}')

        # CDM implements edges (dashed, subdued)
        for v in self.domain_views:
            parent = self._get_cdm_parent(v)
            if parent and parent in added and v not in describable_fringe:
                lines.append(f'    {parent} -.-> {self._sanitize(v)}')

        if describable_fringe and 'CogniteDescribable' in added:
            anchor = self._sanitize(sorted(describable_fringe)[0], record=False)
            lines.append(f'    CogniteDescribable -.->|implements| {anchor}')

        for cp in cdm_parents:
            pp_view = self.all_views.get(cp, {})
            for pp in pp_view.get('implements', '').split(','):
                pp = pp.strip().replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
                if pp and pp in added:
                    lines.append(f'    {pp} -.-> {cp}')

        lines.append('    classDef cdm fill:#1e3a5f,stroke:#3b82f6,stroke-width:1px,color:#93c5fd,stroke-dasharray:5 5')

        for idx, (_, cluster_views) in enumerate(self.clusters.items()):
            color = cluster_colors[idx % len(cluster_colors)]
            for v in cluster_views:
                lines.append(f'    style {self._sanitize(v)} fill:{color},color:#fff,stroke:#fff,stroke-width:2px')

        lines.extend(self._click_lines(added))

        return f'''
            <div class="er-diagram-box">
                <h3>Level 4: {self.model_name} - Full Architecture</h3>
                <p class="diagram-desc">Complete domain model with CDM foundation. Solid edges = data relations, dashed = implements.</p>
                <pre class="mermaid-source">
{chr(10).join(lines)}
                </pre>
            </div>'''
    

    # =========================================================================
    # LEVEL 5: ALL RELATIONS WITH FULL CDM IMPLEMENTS
    # =========================================================================

    def level5_all_relations(self):
        """All domain views, every data relation, and every CDM implements arrow."""
        if len(self.domain_views) < 2:
            return ""

        lines = ["flowchart TB"]
        cluster_colors = ["#3b82f6","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899","#06b6d4"]
        domain_rels_only = self._get_domain_relations(include_cdm_targets=False)
        all_rels = self._get_domain_relations(include_cdm_targets=True)
        describable_fringe = set(self._get_describable_fringe(domain_rels_only))
        domain_ids = set(self.domain_views.keys())

        # Collect every CDM type referenced in implements across all domain views
        cdm_all_set = set()
        for v in self.domain_views:
            for impl in self.all_views.get(v, {}).get("implements", "").split(","):
                impl = impl.strip().replace("cdf_cdm:", "").replace("(version=v1)", "").strip()
                if impl.startswith("Cognite"):
                    cdm_all_set.add(impl)
        # Add CDM data-relation targets
        for r in all_rels:
            if r["target"] not in domain_ids:
                cdm_all_set.add(r["target"])
        # Walk one level up the CDM implements chain so parents appear too
        for cp in list(cdm_all_set):
            for impl in self.all_views.get(cp, {}).get("implements", "").split(","):
                impl = impl.strip().replace("cdf_cdm:", "").replace("(version=v1)", "").strip()
                if impl.startswith("Cognite"):
                    cdm_all_set.add(impl)
        cdm_all = sorted(cdm_all_set)

        # Domain sections (vertical-spine layout)
        sg_lines, inv_lines, spine_anchors, added = self._build_vertical_sections(
            describable_fringe, domain_rels_only)
        lines.extend(sg_lines)
        lines.extend(inv_lines)

        # Catch-all: emit any domain view not yet in 'added' (e.g. no-cluster singletons)
        unclustered = [v for v in sorted(self.domain_views.keys()) if v not in added]
        if unclustered:
            for v in unclustered:
                s = self._sanitize(v)
                self._register_node(v)
                lines.append(f'    {s}["{self._get_label(v)}"]')
                added.add(v)

        # CDM Foundation subgraph
        if cdm_all:
            lines.append('    subgraph CDM["CDM Foundation"]')
            for cp in cdm_all:
                lines.append(f'        {cp}(["{cp}"]):::cdm')
                self._register_node(cp)
                added.add(cp)
            lines.append("    end")
            if spine_anchors:
                lines.append(f'    {spine_anchors[-1]} ~~~ {self._sanitize(cdm_all[0], record=False)}')

        # Data relation edges
        seen_edges = set()
        for rel in all_rels:
            src, tgt = rel["source"], rel["target"]
            key = (src, tgt)
            if key not in seen_edges and src in added and tgt in added:
                seen_edges.add(key)
                prop = (rel.get("display_name") or rel.get("property", ""))[:15]
                mult = self._get_multiplicity(rel)
                lines.append(f'    {self._sanitize(src)} -->|"{prop} [{mult}]"| {self._sanitize(tgt)}')

        # Implements arrows: every domain view → every CDM type it lists
        for v in self.domain_views:
            for impl in self.all_views.get(v, {}).get("implements", "").split(","):
                impl = impl.strip().replace("cdf_cdm:", "").replace("(version=v1)", "").strip()
                if impl.startswith("Cognite") and impl in added:
                    lines.append(
                        f'    {self._sanitize(v)} -.->|implements| {self._sanitize(impl, record=False)}')

        # CDM-to-CDM implements arrows (hierarchy within the CDM Foundation)
        for cp in cdm_all:
            for impl in self.all_views.get(cp, {}).get("implements", "").split(","):
                impl = impl.strip().replace("cdf_cdm:", "").replace("(version=v1)", "").strip()
                if impl.startswith("Cognite") and impl in added:
                    lines.append(
                        f'    {self._sanitize(cp, record=False)} -.->|implements| {self._sanitize(impl, record=False)}')

        lines.append("    classDef cdm fill:#1e3a5f,stroke:#3b82f6,stroke-width:1px,color:#93c5fd,stroke-dasharray:5 5")
        for idx, (_, cluster_views) in enumerate(self.clusters.items()):
            color = cluster_colors[idx % len(cluster_colors)]
            for v in cluster_views:
                if v in added:
                    lines.append(f'    style {self._sanitize(v)} fill:{color},color:#fff,stroke:#fff,stroke-width:2px')

        lines.extend(self._click_lines(added))

        return f"""
            <div class="er-diagram-box">
                <h3>Level 5: {self.model_name} - All Relations incl. CDM Implements</h3>
                <p class="diagram-desc">Every domain view, every data relation, and every CDM implementation chain shown explicitly. Solid arrows = data relations, dashed = implements hierarchy. Click any view for details.</p>
                <pre class="mermaid-source">
{chr(10).join(lines)}
                </pre>
            </div>"""


    # =========================================================================
    # ORCHESTRATION
    # =========================================================================
    
    def generate_all(self):
        """Generate all diagram levels, domain-model-centric."""
        diagrams = []
        
        # Level 1: Domain Overview
        diagrams.append('<h2 class="diagram-level">Level 1: Domain Model Overview</h2>')
        diagrams.append('<p class="level-desc">High-level view of domain structure with functional groupings</p>')
        d = self.level1_domain_overview()
        if d:
            diagrams.append(d)
        
        # Level 2: Per-entity relationship focus
        diagrams.append('<h2 class="diagram-level">Level 2: Entity Relationship Focus</h2>')
        diagrams.append('<p class="level-desc">One diagram per entity — focus entity (blue), outgoing targets (green), incoming sources (amber)</p>')
        # Sort by cluster membership so related entities appear together
        ordered = []
        seen_in_cluster = set()
        for _, cluster_views in self.clusters.items():
            for v in cluster_views:
                ordered.append(v)
                seen_in_cluster.add(v)
        for v in sorted(self.domain_views.keys()):
            if v not in seen_in_cluster:
                ordered.append(v)
        for view_id in ordered:
            d = self.level2_entity_focus(view_id)
            if d:
                diagrams.append(d)
        
        # Level 3: Domain-only Relationship Map
        diagrams.append('<h2 class="diagram-level">Level 3: Domain Relationship Map</h2>')
        diagrams.append('<p class="level-desc">All domain views and data relations — no CDM infrastructure. Pure domain-to-domain signal.</p>')
        d = self.level3_relationship_map()
        if d:
            diagrams.append(d)
        
        # Level 4: Full Architecture with CDM Foundation
        diagrams.append('<h2 class="diagram-level">Level 4: Full Architecture with CDM Foundation</h2>')
        diagrams.append('<p class="level-desc">Domain views + complete CDM foundation + implements arrows + CDM hierarchy. Shows how the domain model fits into the Cognite Data Model.</p>')
        d = self.level4_full_architecture()
        if d:
            diagrams.append(d)
        
        # Level 5: All Relations incl. CDM Implements
        diagrams.append('<h2 class="diagram-level">Level 5: All Relations incl. CDM Implements</h2>')
        diagrams.append('<p class="level-desc">Every domain view with all data relations and every CDM implementation chain shown explicitly</p>')
        d = self.level5_all_relations()
        if d:
            diagrams.append(d)
        
        return '\n'.join(diagrams), self.node_mapping


def generate_overview_diagram(views, all_views, direct_relations, model_name, domain_view_ids=None):
    """Generate a domain-centric overview diagram for the front page."""
    domain_ids = domain_view_ids or set()
    
    domain_views = {}
    for vid, vinfo in views.items():
        if domain_ids:
            if vid in domain_ids:
                domain_views[vid] = vinfo
        else:
            if not vid.startswith('Cognite'):
                domain_views[vid] = vinfo
    
    if not domain_views:
        return ''
    
    def sanitize(s):
        return re.sub(r'[^a-zA-Z0-9]', '_', s)[:20]
    
    def get_label(vid):
        def _clean(s):
            return s.replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
        if vid in views:
            name = _clean(views[vid].get('display_name') or views[vid].get('name', ''))
            if name and name != vid:
                return name
        return vid
    
    def get_cdm_parent(vid):
        view = all_views.get(vid, {})
        impl = view.get('implements', '')
        if impl:
            for p in impl.split(','):
                p = p.strip().replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
                if p.startswith('Cognite'):
                    return p
        return None
    
    content_lines = []
    added = set()
    
    # Group domain views by CDM parent
    by_parent = defaultdict(list)
    for vid in domain_views:
        parent = get_cdm_parent(vid)
        by_parent[parent or 'Other'].append(vid)
    
    # Add domain views grouped by CDM parent
    for parent_type, child_views in sorted(by_parent.items()):
        if parent_type != 'Other':
            parent_sid = sanitize(parent_type)
            content_lines.append(f'    {parent_sid}(["{parent_type}"]):::cdm')
            added.add(parent_sid)
        
        for vid in child_views[:8]:
            label = get_label(vid)[:20]
            sid = sanitize(vid)
            content_lines.append(f'    {sid}["{label}"]')
            if parent_type != 'Other':
                parent_sid = sanitize(parent_type)
                content_lines.append(f'    {parent_sid} -.-> {sid}')
            added.add(sid)
    
    # Add key relationships between domain views
    domain_ids_set = set(domain_views.keys())
    rel_count = 0
    seen = set()
    for rel in direct_relations:
        src, tgt = rel['source'], rel['target']
        if src in domain_ids_set and tgt in domain_ids_set and rel_count < 15:
            edge_key = (src, tgt)
            if edge_key not in seen:
                seen.add(edge_key)
                prop = rel.get('display_name') or rel.get('property', '')
                content_lines.append(f'    {sanitize(src)} -->|"{prop[:12]}"| {sanitize(tgt)}')
                rel_count += 1
    
    content_lines.append('')
    content_lines.append('    classDef cdm fill:#f1f5f9,stroke:#94a3b8,stroke-width:1px,color:#64748b,stroke-dasharray:5 5')
    
    # Style domain views
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
    for i, vid in enumerate(domain_views):
        sid = sanitize(vid)
        color = colors[i % len(colors)]
        content_lines.append(f'    style {sid} fill:{color},color:#fff,stroke:#fff,stroke-width:2px')
    
    # Click directives for all views (domain + CDM parents)
    # Use sanitized node-id as callback arg — colons in view IDs break Mermaid 11
    for vid in domain_views:
        sid = sanitize(vid)
        content_lines.append(f'    click {sid} call openModalFromDiagram("{sid}")')
    for parent_type in by_parent:
        if parent_type != 'Other' and parent_type.startswith('Cognite'):
            parent_sid = sanitize(parent_type)
            content_lines.append(f'    click {parent_sid} call openModalFromDiagram("{parent_sid}")')
    
    return f'''
        <div class="overview-diagram">
            <h3>Model Structure</h3>
            <p class="diagram-desc">{model_name} - Domain Model Overview</p>
            <pre class="mermaid-source">
flowchart TB
{chr(10).join(content_lines)}
            </pre>
        </div>'''


# =============================================================================
# ICON GENERATION
# =============================================================================

def generate_icons(views):
    """Generate icons for views."""
    icons = {}
    
    patterns = {
        '🛢️': ['well', 'oil', 'petroleum'],
        '🔝': ['wellhead'],
        '⬆️': ['als', 'lift'],
        '⚡': ['electrical', 'power', 'vsd', 'transformer'],
        '💨': ['gas', 'vapor'],
        '🔄': ['pump', 'compressor'],
        '🌀': ['turbine', 'fan', 'motor'],
        '🛢': ['tank', 'storage', 'vessel'],
        '⚗️': ['separator', 'filter', 'exchanger'],
        '🗺️': ['field', 'area', 'zone', 'structure'],
        '💎': ['reservoir', 'formation', 'pattern'],
        '🏭': ['facility', 'plant', 'factory', 'site', 'warehouse'],
        '📊': ['timeseries', 'sensor', 'measurement', 'series', 'forecast'],
        '📄': ['document', 'file', 'drawing', 'datasheet', 'revision'],
        '🎯': ['tag'],
        '⏱️': ['timetag'],
        '🔧': ['maintenance', 'repair', 'workorder'],
        '📋': ['project', 'activity', 'task', 'event'],
        '🏛️': ['org', 'company', 'organization', 'contract'],
        '🔌': ['source', 'integration'],
        '🎨': ['3d', 'cad', 'visual', 'model', 'image'],
        '🏷️': ['class', 'type', 'category', 'status'],
        '⚙️': ['equipment', 'component'],
        '🎛️': ['instrument', 'meter', 'valve', 'plc'],
    }
    
    for view_id, view_info in views.items():
        display_name = (view_info.get('display_name') or view_info.get('name', view_id)).lower()
        combined = f"{view_id.lower()} {display_name}"
        
        for icon, pats in patterns.items():
            if any(p in combined for p in pats):
                icons[view_id] = icon
                break
        else:
            if 'asset' in combined:
                icons[view_id] = '🏭'
            elif 'equipment' in combined:
                icons[view_id] = '⚙️'
            elif 'time' in combined:
                icons[view_id] = '📊'
            elif 'file' in combined:
                icons[view_id] = '📄'
            elif 'activ' in combined:
                icons[view_id] = '📋'
            else:
                icons[view_id] = '📦'
    
    return icons


# =============================================================================
# HTML GENERATION
# =============================================================================

def escape_html(text):
    if not text:
        return ''
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def simplify_type(type_str):
    if not type_str:
        return 'text'
    type_str = str(type_str)
    type_str = re.sub(r'\(.*?\)', '', type_str)
    type_str = type_str.replace('cdf_cdm:', '').strip()
    return type_str


def _type_css_class(ptype):
    """Return a CSS class name for a scalar value type."""
    p = ptype.lower()
    if p in ('float32', 'float64'):
        return 'prop-type-float'
    if p in ('int32', 'int64'):
        return 'prop-type-int'
    if p == 'boolean':
        return 'prop-type-boolean'
    if p in ('timestamp', 'date'):
        return 'prop-type-datetime'
    if p == 'json':
        return 'prop-type-json'
    if p in ('timeseries', 'file', 'sequence'):
        return 'prop-type-special'
    if p in ('direct_relation', 'node'):
        return 'prop-type-node'
    return 'prop-type-text'


def generate_property_table(props, view_id, inheritance_depths, all_views):
    """Generate HTML property table."""
    html_parts = []
    
    own_props = [p for p in props if p.get('inherited_from') is None]
    inherited_props = [p for p in props if p.get('inherited_from') is not None]
    
    def format_source_title(source):
        if re.match(r'^(CFIHOS_|EPC_|TCFIHOS_)', source):
            if source in all_views and all_views[source].get('display_name'):
                return f"{all_views[source]['display_name']} ({source})"
        return source
    
    def make_prop_row(prop):
        # View Property fields
        view_prop = escape_html(prop.get('name', ''))
        view_prop_name = prop.get('display_name', '')
        
        # Container Property fields
        container_prop = prop.get('container_property', '')
        container_prop_name = prop.get('container_property_name', '')
        
        ptype = simplify_type(prop.get('type', 'text'))
        desc = escape_html(prop.get('description', ''))[:80]
        if len(prop.get('description', '')) > 80:
            desc += '...'
        
        connection = prop.get('connection', 'null')
        is_relation = connection and connection != 'null'
        type_class = 'prop-type-relation' if is_relation else _type_css_class(ptype)
        
        # Type column - show both externalId and display name for targets
        if is_relation:
            type_id = ptype
            type_name = None
            if type_id in all_views:
                type_name = all_views[type_id].get('display_name') or all_views[type_id].get('name')
            
            if type_name and type_name != type_id:
                type_display = f'&rarr; <span class="type-name">{escape_html(type_name)}</span><br/><span class="type-code">{type_id}</span>'
            else:
                type_display = f'&rarr; {escape_html(ptype)}'
        else:
            type_display = escape_html(ptype)
        
        min_count = prop.get('min_count', '0')
        max_count = prop.get('max_count', '1')
        cardinality = f'{min_count}..{max_count}'
        try:
            if max_count == '1000' or (max_count and max_count != 'null' and int(max_count) > 1):
                cardinality += ' (list)'
        except:
            pass
        
        # View Property column - show name and externalId
        if view_prop_name and view_prop_name != view_prop:
            view_display = f'<span class="type-name">{escape_html(view_prop_name)}</span><br/><span class="type-code">{view_prop}</span>'
        else:
            view_display = escape_html(view_prop)
        
        # Container Property column - show name and externalId
        if container_prop:
            if container_prop_name and container_prop_name != container_prop:
                container_display = f'<span class="type-name">{escape_html(container_prop_name)}</span><br/><span class="type-code">{escape_html(container_prop)}</span>'
            else:
                container_display = f'<span class="type-code">{escape_html(container_prop)}</span>'
        else:
            container_display = '<span class="text-muted">—</span>'
        
        return f'<tr><td class="prop-name">{view_display}</td><td class="prop-container">{container_display}</td><td class="prop-type {type_class}">{type_display}</td><td class="prop-card">{cardinality}</td><td class="prop-desc">{desc}</td></tr>'
    
    def get_icon(source):
        icons = {'Describable': '🏷️', 'Sourceable': '📥', 'Visualizable': '👁️', 
                 'Schedulable': '📅', 'Asset': '🏭', 'Equipment': '⚙️',
                 'TimeSeries': '📊', 'Activity': '⚡', 'File': '📁'}
        for key, icon in icons.items():
            if key in source:
                return icon
        return '📦'
    
    table_header = '<tr><th>View Property</th><th>Container Property</th><th>Type</th><th>Card.</th><th>Description</th></tr>'
    
    if own_props:
        html_parts.append(f'''
        <div class="prop-section own-section">
            <div class="section-title">Own Properties ({len(own_props)})</div>
            <table class="prop-table">
                {table_header}
                {''.join(make_prop_row(p) for p in own_props)}
            </table>
        </div>''')
    
    if inherited_props:
        by_source = defaultdict(list)
        source_order = []
        for prop in inherited_props:
            source = prop.get('inherited_from', 'Unknown').replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
            if source not in by_source:
                source_order.append(source)
            by_source[source].append(prop)
        
        source_order.sort(key=lambda s: inheritance_depths.get(s, 0), reverse=True)
        
        for source in source_order:
            source_props = by_source[source]
            icon = get_icon(source)
            title = format_source_title(source)
            
            html_parts.append(f'''
        <div class="prop-section inherited-section">
            <div class="section-title">{icon} from {title} ({len(source_props)})</div>
            <table class="prop-table">
                {table_header}
                {''.join(make_prop_row(p) for p in source_props)}
            </table>
        </div>''')
    
    return '\n'.join(html_parts)


def generate_card(view_id, view_data, icon, cat_class, inheritance_depths, all_views, view_domains=None):
    """Generate HTML card for a view with industry domain tags."""
    props = view_data['properties']
    total_count = len(props)
    own_count = view_data.get('own_property_count', total_count)
    inherited_count = view_data.get('inherited_property_count', 0)
    description = view_data.get('description', '') or f'{view_data.get("name", view_id)} entity'
    implements = view_data.get('implements', '')
    
    impl_parts = []
    for impl in implements.split(','):
        impl = impl.strip().replace('(version=v1)', '').replace('cdf_cdm:', '').strip()
        if impl:
            impl_parts.append(impl)
    impl_text = ', '.join(impl_parts[:2]) if impl_parts else 'Base'
    if len(impl_parts) > 2:
        impl_text += f' +{len(impl_parts)-2}'
    
    if inherited_count > 0:
        prop_display = f'{own_count} + {inherited_count}'
        prop_summary = f'{own_count} Own + {inherited_count} Inherited = {total_count} Total'
    else:
        prop_display = f'{total_count}'
        prop_summary = f'{total_count} Properties'
    
    display_name = view_data.get('display_name') or view_data.get('name', '')
    if re.match(r'^(CFIHOS_|EPC_|TCFIHOS_)', view_id):
        if display_name and display_name != view_id:
            title = f'{escape_html(display_name)} <span class="view-code">({view_id})</span>'
        else:
            title = view_id
    else:
        title = view_id
    
    # Domain tag removed - standards are used internally for categorization only
    domain_tag = ''
    
    return f'''
                <div class="card" data-view-id="{view_id}" data-node-id="{view_id.replace(':', '_')}">
                    <div class="card-main" onclick="toggleCard(this.parentElement)">
                        <div class="card-header">
                            <div class="card-icon {cat_class}">{icon}</div>
                            <div><div class="card-title">{title}</div>{domain_tag}</div>
                            <button class="btn-expand" onclick="event.stopPropagation(); openModal('{view_id}')" title="Expand">&#x26F6;</button>
                        </div>
                        <div class="card-description">{escape_html(description)[:150]}{'...' if len(description) > 150 else ''}</div>
                        <div class="card-footer">
                            <span class="card-implements">extends {impl_text}</span>
                            <span class="card-expand">{prop_display} props</span>
                        </div>
                    </div>
                    <div class="card-properties">
                        <div class="prop-count">{prop_summary}</div>
                        <div class="prop-sections">
{generate_property_table(props, view_id, inheritance_depths, all_views)}
                        </div>
                    </div>
                </div>'''


# =============================================================================
# CLASS HIERARCHY
# =============================================================================

def generate_class_hierarchy(views, all_views, domain_view_ids):
    """Generate an interactive collapsible class hierarchy tree (HTML string)."""
    from collections import defaultdict

    def _norm_impl(raw):
        p = raw.strip()
        if p.startswith('cdf_cdm:'):
            p = p[len('cdf_cdm:'):]
        if '(version=' in p:
            p = p[:p.index('(version=')].strip()
        return p if p else None

    # IDM views are stored under TWO keys in all_views: a plain name (e.g. 'CogniteOperation',
    # marked _idm_specific=True at load time) AND a cdf_idm:-prefixed canonical key.
    # The plain-name dupe must NOT be treated as a CDM type.
    # We use the _idm_specific marker set during IDM loading so that CDM views sharing the same
    # name (the IDM YAML is a superset of CDM) are NOT incorrectly treated as dupes.
    idm_plain_dupes = {
        vid for vid, info in all_views.items()
        if info.get('_idm_specific') and not vid.startswith('cdf_idm:')
    }

    def _direct_parents(vid):
        """Return only the direct (non-redundant) parents of vid.

        NEAT stores the full flat transitive implements list, so a view that
        implements CogniteActivity will also list CogniteDescribable (the
        grandparent) explicitly.  We drop any parent that is itself an ancestor
        of another parent in the same list, keeping only the closest ones.
        """
        info = all_views.get(vid, {})
        impl = info.get('implements', '')
        if not impl:
            return []
        all_p = []
        for raw in impl.split(','):
            p = _norm_impl(raw)
            if p and p not in idm_plain_dupes:
                all_p.append(p)
        if len(all_p) <= 1:
            return all_p

        def _ancestors(nid, _seen=None):
            if _seen is None:
                _seen = set()
            if nid in _seen:
                return _seen
            _seen.add(nid)
            for raw2 in (all_views.get(nid, {}).get('implements', '') or '').split(','):
                p2 = _norm_impl(raw2)
                if p2 and p2 not in idm_plain_dupes:
                    _ancestors(p2, _seen)
            return _seen

        anc = {p: _ancestors(p) - {p} for p in all_p}
        return [p for p in all_p
                if not any(p in anc.get(q, set()) for q in all_p if q != p)]

    children_map = defaultdict(list)
    has_parent = set()
    for vid, info in all_views.items():
        if vid in idm_plain_dupes:
            continue  # use only the cdf_idm: canonical key
        for parent in _direct_parents(vid):
            children_map[parent].append(vid)
            has_parent.add(vid)

    # True CDM types: start with 'Cognite' but are NOT IDM plain-name duplicates
    cdm_ids    = {v for v in all_views if v.startswith('Cognite') and v not in idm_plain_dupes}
    idm_ids    = {v for v in all_views if v.startswith('cdf_idm:')}
    domain_ids = set(domain_view_ids or [])

    # Only include CDM/IDM types that are actually reachable via the implements chain
    # of domain views (transitive ancestors), not the full CDM/IDM catalogue.
    used_cdm_idm = set()

    def _collect_ancestors(vid, _seen=None):
        if _seen is None:
            _seen = set()
        if vid in _seen:
            return
        _seen.add(vid)
        info = all_views.get(vid, {})
        impl = info.get('implements', '')
        if not impl:
            return
        for raw in impl.split(','):
            parent = _norm_impl(raw)
            if not parent or parent in idm_plain_dupes:
                continue
            if parent in cdm_ids or parent in idm_ids:
                used_cdm_idm.add(parent)
            _collect_ancestors(parent, _seen)

    for vid in domain_ids:
        _collect_ancestors(vid)

    relevant = used_cdm_idm | domain_ids

    def is_relevant(n):
        return n in relevant

    def node_kind(n):
        if n.startswith('cdf_idm:'):
            return 'idm'
        if n.startswith('Cognite') and n not in idm_plain_dupes:
            return 'cdm'
        if n in domain_ids:
            return 'domain'
        return 'other'

    def disp(n):
        """Return the display label for a hierarchy node.
        CDM/IDM types show their full space:externalId(version=<ver>) identifier,
        where version comes from the model metadata stored at load time.
        Domain views show their human-readable display name."""
        info = all_views.get(n, {})
        ver   = info.get('_model_version', '') or ''
        space = info.get('_model_space',   '') or ''
        ver_str = f'(version={ver})' if ver else ''
        if n.startswith('cdf_idm:'):
            base = n[len('cdf_idm:'):]
            ns = space or 'cdf_idm'
            return f'{ns}:{base}{ver_str}'
        if n.startswith('Cognite') and n not in idm_plain_dupes:
            ns = space or 'cdf_cdm'
            return f'{ns}:{n}{ver_str}'
        # Domain view — use human-readable display name
        return info.get('display_name') or info.get('name', '') or n

    has_card  = set(views.keys())
    all_nodes = set(all_views.keys()) | set(children_map.keys())
    roots = sorted(
        (n for n in all_nodes if n not in has_parent and is_relevant(n)),
        key=lambda n: (0 if n.startswith('Cognite') else (1 if n.startswith('cdf_idm:') else 2), n)
    )

    def render(n, branch=None):
        """Render node n.  branch is the set of ancestor IDs on the current path —
        used only to break cycles in the (rare) case of circular implements chains.
        The same node may appear under multiple parents (multiple inheritance)."""
        if branch is None:
            branch = frozenset()
        if n in branch:           # cycle guard only — not a global visited check
            return ''

        if not is_relevant(n):
            # Transparent intermediary — surface its relevant children in place
            new_branch = branch | {n}
            return ''.join(render(c, new_branch)
                           for c in sorted(set(children_map.get(n, []))))

        kind  = node_kind(n)
        dname = escape_html(disp(n))
        dname_lc = dname.lower().replace('"', '&quot;')

        raw_ch = list(dict.fromkeys(children_map.get(n, [])))
        rel_ch = sorted(
            {c for c in raw_ch
             if is_relevant(c) or any(is_relevant(g) for g in children_map.get(c, []))},
            key=lambda c: (0 if c.startswith('Cognite') else (1 if c.startswith('cdf_idm:') else 2), c)
        )

        info_v    = all_views.get(n, {})
        own_props = [p for p in info_v.get('properties', []) if not p.get('inherited_from')]
        pbadge    = (f'<span class="hier-prop-badge" title="Own properties">{len(own_props)}p</span>'
                     if own_props else '')

        kbadge = ''
        if kind == 'idm':
            kbadge = '<span class="hier-kind-badge hier-badge-idm">IDM</span>'
        elif kind == 'cdm':
            kbadge = '<span class="hier-kind-badge hier-badge-cdm">CDM</span>'

        # ALL relevant nodes are clickable via hierClick (falls back to info popup for non-card views)
        safe_n = n.replace('\\', '\\\\').replace("'", "\\'")
        onclick_attr = f' onclick="hierClick(\'{safe_n}\')" title="View details"'
        cc = ' hier-clickable'

        label = f'<span class="hier-label hier-{kind}{cc}"{onclick_attr}>{dname}</span>'

        # Render children FIRST, then decide toggle based on whether anything rendered
        new_branch = branch | {n}
        ch_html = ''
        if rel_ch:
            ch_items = ''.join(render(c, new_branch) for c in rel_ch)
            if ch_items.strip():
                ch_html = f'<ul class="hier-children" style="display:none">{ch_items}</ul>'

        # Toggle only if children actually rendered (avoids orphan toggle buttons)
        toggle = ('<button class="hier-toggle" onclick="hierToggle(this)">&#9658;</button>'
                  if ch_html else '<span class="hier-leaf-spacer"></span>')

        return (f'<li class="hier-node hier-node-{kind}" data-name="{dname_lc}" data-view-id="{n}">'
                f'<div class="hier-row">{toggle}{label}{kbadge}{pbadge}</div>'
                f'{ch_html}</li>')

    root_html = ''.join(render(r, frozenset()) for r in roots)

    cdm_c = len([n for n in used_cdm_idm if n.startswith('Cognite') and n not in idm_plain_dupes])
    idm_c = len([n for n in used_cdm_idm if n.startswith('cdf_idm:')] +
                [n for n in domain_ids if n.startswith('cdf_idm:')])
    dom_c = len(domain_ids)
    tot   = cdm_c + idm_c + dom_c

    stats = (f'{tot} types &nbsp;&middot;&nbsp; '
             f'<span style="color:#60a5fa">{cdm_c} CDM</span> &nbsp;&middot;&nbsp; '
             f'<span style="color:#fb923c">{idm_c} IDM</span> &nbsp;&middot;&nbsp; '
             f'<span style="color:#4ade80">{dom_c} domain</span>')

    return f'''<div class="hierarchy-wrap">
<div class="hierarchy-toolbar">
  <span class="hier-stats">{stats}</span>
  <button class="hier-ctrl-btn" onclick="hierExpandAll()">&#9660; Expand All</button>
  <button class="hier-ctrl-btn" onclick="hierCollapseAll()">&#9658; Collapse All</button>
  <input type="text" class="hier-filter-input" placeholder="&#128269; Filter by name\u2026" oninput="hierFilter(this.value)">
</div>
<div class="hierarchy-legend">
  <span class="hier-legend-item"><span class="hier-cdm">&#9632;</span> cdf_cdm \u2013 Cognite Data Model (used base types only)</span>
  <span class="hier-legend-item"><span class="hier-idm">&#9632;</span> cdf_idm \u2013 Industry Data Model (used types only)</span>
  <span class="hier-legend-item"><span class="hier-domain hier-clickable">&#9632;</span> Domain \u2013 this model\u2019s entities (click for details)</span>
</div>
<ul class="hier-root">{root_html}</ul>
</div>'''


def generate_html(model_name, space, description, views, all_views, inheritance_depths, 
                  categories, category_labels, icons, direct_relations, view_domains=None,
                  domain_view_ids=None, external_id=None, version=None):
    """Generate complete HTML documentation with industry domain categorization."""
    
    sections = {}
    for cat, view_ids in categories.items():
        cards = []
        for view_id in view_ids:
            if view_id in views:
                icon = icons.get(view_id, category_labels.get(cat, ('📦', '', ''))[0])
                cat_class = f'cat-{cat.replace("_", "-")}'
                cards.append(generate_card(view_id, views[view_id], icon, cat_class, inheritance_depths, all_views, view_domains))
        sections[cat] = '\n'.join(cards)
    
    total_props = sum(len(v.get('properties', [])) for v in views.values())
    total_views = len(views)
    total_relations = len(direct_relations)
    
    # Generate diagrams
    diagram_gen = UMLDiagramGenerator(views, all_views, direct_relations, model_name,
                                      domain_view_ids=domain_view_ids)
    er_diagrams, node_mapping = diagram_gen.generate_all()
    overview_diagram = generate_overview_diagram(views, all_views, direct_relations, model_name,
                                                 domain_view_ids=domain_view_ids)
    
    # Convert node mapping to JavaScript
    import json
    node_mapping_js = json.dumps(node_mapping)

    # Generate class hierarchy
    hierarchy_html = generate_class_hierarchy(views, all_views, domain_view_ids)

    # Build lightweight view data for CDM/IDM nodes that don't have full entity cards.
    # Exclude plain-name IDM duplicates (marked _idm_specific at load time, no cdf_idm: prefix).
    _hier_card_ids = set(views.keys())
    _hier_idm_dupes = {v for v, info in all_views.items()
                       if info.get('_idm_specific') and not v.startswith('cdf_idm:')}
    _hier_extra = {}
    _hier_all_relevant = (
        {v for v in all_views if v.startswith('Cognite') and v not in _hier_idm_dupes} |
        {v for v in all_views if v.startswith('cdf_idm:')} |
        set(domain_view_ids or [])
    )
    for _nid in _hier_all_relevant:
        if _nid not in _hier_card_ids:
            _info = all_views.get(_nid, {})
            # Use space:id(version) format for CDM/IDM types in the popup title;
            # version and space come from metadata stored at load time.
            _ver   = _info.get('_model_version', '') or ''
            _space = _info.get('_model_space',   '') or ''
            _vstr  = f'(version={_ver})' if _ver else ''
            if _nid.startswith('cdf_idm:'):
                _base = _nid[len('cdf_idm:'):]
                _disp_name = f'{_space or "cdf_idm"}:{_base}{_vstr}'
            elif _nid.startswith('Cognite'):
                _disp_name = f'{_space or "cdf_cdm"}:{_nid}{_vstr}'
            else:
                _disp_name = _info.get('display_name') or _info.get('name') or _nid
            _hier_extra[_nid] = {
                'name': _disp_name,
                'desc': (_info.get('description') or '')[:300],
                'kind': ('idm' if _nid.startswith('cdf_idm:') else 'cdm'),
                'props': len(_info.get('properties', [])),
            }
    hier_extra_js = json.dumps(_hier_extra)

    # Generate search data
    search_data = {}
    for view_id, view_data in views.items():
        domain_info = view_domains.get(view_id, {}) if view_domains else {}
        domain_id = domain_info.get('domain', '')
        domain_display = DOMAIN_CATEGORIES.get(domain_id, {}).get('display_name', domain_id)
        
        # Get view's display name (for code-based IDs like CFIHOS_xxx)
        view_display_name = view_data.get('display_name') or view_data.get('name', view_id)
        
        # Extract property info for search - include all 4 property identifiers
        props_for_search = []
        for prop in view_data.get('properties', []):  # Include all properties
            # View Property fields
            view_prop = prop.get('name', '')
            view_prop_name = prop.get('display_name', '')
            
            # Container Property fields
            container_prop = prop.get('container_property', '')
            container_prop_name = prop.get('container_property_name', '')
            
            prop_type = prop.get('type', '').replace('cdf_cdm:', '').replace('(version=v1)', '').strip()
            
            # Get target display name if it's a relation
            target_display = ''
            if prop_type and prop_type in all_views:
                target_view = all_views.get(prop_type, {})
                target_display = target_view.get('display_name') or target_view.get('name', prop_type)
            
            props_for_search.append({
                'viewProperty': view_prop,  # View Property externalId
                'viewPropertyName': view_prop_name,  # View Property display name
                'containerProperty': container_prop,  # Container Property externalId
                'containerPropertyName': container_prop_name,  # Container Property display name
                'type': prop_type,  # Target type (externalId)
                'typeDisplay': target_display,  # Target type display name
                'isRelation': bool(prop.get('connection') and prop.get('connection') != 'null'),
                'inherited': bool(prop.get('inherited_from')),
            })
        
        search_data[view_id] = {
            'displayName': view_display_name,
            'description': (view_data.get('description', '') or '')[:200],
            'domain': domain_id,
            'domainDisplay': domain_display,
            'properties': props_for_search,
        }
    
    search_data_js = json.dumps(search_data)
    
    nav_tabs = ['<button class="nav-tab active" onclick="showSection(\'overview\')">Overview</button>']

    # Fixed order: Entity Hierarchy → CDM Core Types → IDM Industry Types → remaining → ER Diagrams
    nav_tabs.append('<button class="nav-tab" onclick="showSection(\'hierarchy\')">&#127960; Entity Hierarchy</button>')

    _PINNED_CATS = ('cdm_core', 'idm_types')
    for cat in _PINNED_CATS:
        if cat in categories and cat in sections and sections[cat]:
            icon, label, _ = category_labels.get(cat, ('📦', cat.title(), ''))
            count = len([v for v in categories[cat] if v in views])
            nav_tabs.append(f'<button class="nav-tab" onclick="showSection(\'{cat}\')">{icon} {label} ({count})</button>')

    for cat in categories:
        if cat in _PINNED_CATS:
            continue  # already added above
        if cat in sections and sections[cat]:
            icon, label, _ = category_labels.get(cat, ('📦', cat.title(), ''))
            count = len([v for v in categories[cat] if v in views])
            nav_tabs.append(f'<button class="nav-tab" onclick="showSection(\'{cat}\')">{icon} {label} ({count})</button>')

    nav_tabs.append('<button class="nav-tab" onclick="showSection(\'erdiagram\')">ER Diagrams</button>')
    
    category_sections = []
    for cat in categories:
        if cat in sections and sections[cat]:
            icon, label, desc = category_labels.get(cat, ('📦', cat.title(), ''))
            category_sections.append(f'''
        <div id="{cat}" class="section">
            <h2 class="section-title">{icon} {label}</h2>
            <p class="section-description">{desc}</p>
            <div class="card-grid">
                {sections[cat]}
            </div>
        </div>''')
    
    _eid = external_id or space
    _version_clean = version.strip("'\"") if version else ''
    _ver = f' (version="{_version_clean}")' if _version_clean else ''
    model_subtitle = f'"{space}":"{_eid}"{_ver}'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{model_name} Documentation</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
    <style>
        :root {{
            --bg-primary: #0c1222;
            --bg-secondary: #141d2f;
            --bg-card: #1a2744;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-color: #2d3f5f;
            --accent-gold: #f59e0b;
            --accent-blue: #3b82f6;
            --accent-emerald: #10b981;
            --accent-purple: #8b5cf6;
            --accent-red: #ef4444;
            --accent-cyan: #06b6d4;
        }}
        
        [data-theme="light"] {{
            --bg-primary: #f1f5f9;
            --bg-secondary: #e2e8f0;
            --bg-card: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #475569;
            --text-muted: #64748b;
            --border-color: #cbd5e1;
            --accent-gold: #d97706;
            --accent-blue: #2563eb;
            --accent-emerald: #059669;
            --accent-purple: #7c3aed;
            --accent-red: #dc2626;
            --accent-cyan: #0891b2;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }}
        
        header {{
            background: linear-gradient(135deg, var(--bg-secondary), var(--bg-card));
            padding: 2rem;
            border-bottom: 1px solid var(--border-color);
            text-align: center;
            position: relative;
        }}
        header h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        header p {{ color: var(--text-secondary); }}
        
        /* Theme Toggle Switch */
        .theme-toggle {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .theme-toggle-label {{
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
        .toggle-switch {{
            position: relative;
            width: 44px;
            height: 22px;
        }}
        .toggle-switch input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}
        .toggle-slider {{
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: var(--bg-primary);
            border: 1px solid var(--border-color);
            transition: 0.3s;
            border-radius: 22px;
        }}
        .toggle-slider:before {{
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 2px;
            bottom: 2px;
            background-color: var(--accent-gold);
            transition: 0.3s;
            border-radius: 50%;
        }}
        .toggle-switch input:checked + .toggle-slider {{
            background-color: var(--accent-blue);
        }}
        .toggle-switch input:checked + .toggle-slider:before {{
            transform: translateX(22px);
            background-color: #fff;
        }}
        .theme-icon {{
            font-size: 1rem;
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 3rem;
            padding: 1.5rem;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
        }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 2rem; font-weight: bold; color: var(--accent-gold); }}
        .stat-label {{ font-size: 0.875rem; color: var(--text-muted); }}
        
        /* Dual Search functionality */
        .search-dual {{
            display: flex;
            gap: 1rem;
            align-items: flex-start;
        }}
        .search-box {{
            position: relative;
            flex: 1;
        }}
        .search-box-inner {{
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            padding: 0.5rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            min-width: 200px;
        }}
        .search-box-label {{
            font-size: 0.65rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .search-input {{
            padding: 0.4rem 0.6rem;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-primary);
            font-size: 0.85rem;
        }}
        .search-input:focus {{
            outline: none;
            border-color: var(--accent-gold);
        }}
        .search-input::placeholder {{
            color: var(--text-muted);
        }}
        .search-filter {{
            font-size: 0.65rem;
            color: var(--accent-gold);
            margin-top: 0.25rem;
        }}
        .search-filter .clear-filter {{
            color: var(--accent-red);
            cursor: pointer;
            margin-left: 0.5rem;
        }}
        .search-filter .clear-filter:hover {{
            text-decoration: underline;
        }}
        .search-help {{
            font-size: 0.7rem;
            color: var(--text-muted);
            max-width: 200px;
            line-height: 1.4;
            padding: 0.5rem;
        }}
        .search-help code {{
            background: var(--bg-primary);
            padding: 0.1rem 0.3rem;
            border-radius: 3px;
            color: var(--accent-gold);
        }}
        .search-results {{
            display: none;
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            max-height: 400px;
            overflow-y: auto;
            z-index: 200;
            margin-top: 4px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
        }}
        .search-results.active {{
            display: block;
        }}
        .search-result-item {{
            padding: 0.75rem 1rem;
            cursor: pointer;
            border-bottom: 1px solid var(--border-color);
            transition: background 0.2s;
        }}
        .search-result-item:hover {{
            background: var(--bg-secondary);
        }}
        .search-result-item:last-child {{
            border-bottom: none;
        }}
        .search-result-title {{
            font-weight: 600;
            color: var(--text-primary);
            font-size: 0.9rem;
        }}
        .search-result-meta {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 2px;
        }}
        .search-result-container {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 2px;
            font-family: 'Consolas', monospace;
        }}
        .search-result-property {{
            font-family: 'Consolas', monospace;
            color: var(--accent-cyan);
        }}
        .search-highlight {{
            background: var(--accent-gold);
            color: var(--bg-primary);
            padding: 0 2px;
            border-radius: 2px;
        }}
        .search-wrapper {{
            position: relative;
        }}
        .search-count {{
            font-size: 0.75rem;
            color: var(--text-muted);
            padding: 0.5rem 1rem;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .nav-tabs {{
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-start;
            gap: 0.5rem;
            padding: 1rem 2rem;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
            max-width: 1600px;
            margin: 0 auto;
        }}
        .nav-tab {{
            padding: 0.4rem 0.75rem;
            border: 1px solid var(--border-color);
            background: var(--bg-card);
            color: var(--text-secondary);
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.8rem;
        }}
        .nav-tab:hover {{ border-color: var(--accent-gold); color: var(--text-primary); }}
        .nav-tab.active {{
            background: var(--accent-gold);
            border-color: var(--accent-gold);
            color: var(--bg-primary);
        }}
        
        .container {{ max-width: 1600px; margin: 0 auto; padding: 2rem; }}
        
        .section {{ display: none; }}
        .section.active {{ display: block; }}
        .section-title {{ font-size: 1.5rem; margin-bottom: 0.5rem; color: var(--accent-gold); }}
        .section-description {{ color: var(--text-secondary); margin-bottom: 1.5rem; }}
        
        /* Overview */
        .overview-diagram {{
            background: var(--bg-secondary);
            border: 2px solid var(--accent-gold);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 2rem 0;
        }}
        .overview-diagram h3 {{ color: var(--accent-gold); margin-bottom: 0.5rem; }}
        .overview-diagram .diagram-desc {{ color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem; }}
        
        /* Cards - 2 columns for wider property tables */
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1rem;
        }}
        @media (max-width: 1200px) {{
            .card-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            overflow: hidden;
            transition: all 0.2s;
        }}
        .card:hover {{ border-color: var(--accent-gold); box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4); }}
        
        .card-main {{ padding: 1rem; cursor: pointer; }}
        .card-header {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; }}
        .card-icon {{
            width: 36px; height: 36px;
            display: flex; align-items: center; justify-content: center;
            border-radius: 8px;
            font-size: 1.2rem;
            flex-shrink: 0;
        }}
        .card-title {{ font-weight: 600; font-size: 0.9rem; word-break: break-word; }}
        .view-code {{ font-size: 0.7rem; color: var(--text-muted); font-weight: normal; }}
        
        /* Domain tags - industry standard badges */
        .domain-tag {{
            display: inline-block;
            font-size: 0.6rem;
            padding: 2px 6px;
            border-radius: 4px;
            margin-top: 2px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        .domain-location-geography {{ background: #059669; color: #fff; }}
        .domain-wells-completions {{ background: #7c3aed; color: #fff; }}
        .domain-subsurface-reservoir {{ background: #9333ea; color: #fff; }}
        .domain-rotating-equipment {{ background: #dc2626; color: #fff; }}
        .domain-static-equipment {{ background: #ea580c; color: #fff; }}
        .domain-piping-valves {{ background: #65a30d; color: #fff; }}
        .domain-electrical-equipment {{ background: #0891b2; color: #fff; }}
        .domain-instrumentation-control {{ background: #2563eb; color: #fff; }}
        .domain-tags-functional-locations {{ background: #4f46e5; color: #fff; }}
        .domain-timeseries-measurements {{ background: #0d9488; color: #fff; }}
        .domain-activities-work {{ background: #ca8a04; color: #000; }}
        .domain-documents-files {{ background: #db2777; color: #fff; }}
        .domain-commercial-procurement {{ background: #be185d; color: #fff; }}
        .domain-epc-project {{ background: #c026d3; color: #fff; }}
        .domain-reference-classification {{ background: #6366f1; color: #fff; }}
        .domain-organizational {{ background: #475569; color: #fff; }}
        .domain-3d-spatial {{ background: #f59e0b; color: #000; }}
        .domain-cdm-core {{ background: #3b82f6; color: #fff; }}
        .domain-cdm-features {{ background: #10b981; color: #fff; }}
        .domain-idm-types {{ background: #f97316; color: #fff; }}
        .domain-model-extensions {{ background: #f59e0b; color: #000; }}
        .card-description {{ font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.5rem; }}
        .card-footer {{ display: flex; justify-content: space-between; font-size: 0.75rem; }}
        .card-implements {{ color: var(--accent-emerald); }}
        .card-expand {{ color: var(--accent-purple); }}
        
        .btn-expand {{
            width: 28px; height: 28px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-secondary);
            cursor: pointer;
            margin-left: auto;
            flex-shrink: 0;
        }}
        .btn-expand:hover {{ border-color: var(--accent-gold); color: var(--accent-gold); }}
        
        .card-properties {{ display: none; padding: 1rem; border-top: 1px solid var(--border-color); background: var(--bg-secondary); }}
        .card.expanded .card-properties {{ display: block; }}
        
        .prop-count {{ font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem; }}
        
        /* Property Tables */
        .prop-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
        .prop-table th {{ 
            text-align: left; 
            padding: 0.3rem 0.5rem; 
            font-size: 0.7rem; 
            color: var(--text-muted); 
            border-bottom: 1px solid var(--border-color);
        }}
        .prop-table th:nth-child(1) {{ width: 20%; }}
        .prop-table th:nth-child(2) {{ width: 18%; }}
        .prop-table th:nth-child(3) {{ width: 18%; }}
        .prop-table th:nth-child(4) {{ width: 10%; }}
        .prop-table th:nth-child(5) {{ width: 34%; }}
        .prop-container {{ color: #94a3b8; font-family: 'Consolas', monospace; line-height: 1.4; }}
        .text-muted {{ color: var(--text-muted); opacity: 0.5; }}
        
        .prop-table td {{ 
            padding: 0.3rem 0.5rem; 
            font-size: 0.7rem; 
            vertical-align: top;
            border-bottom: 1px solid rgba(45, 63, 95, 0.5);
        }}
        
        .prop-name {{ color: #a3aebe; font-family: 'Consolas', monospace; line-height: 1.4; }}
        .prop-type {{ font-family: 'Consolas', monospace; line-height: 1.4; }}
        /* ── Scalar type colours ── */
        .prop-type-text     {{ color: #22d3ee !important; }}   /* cyan    – text / string */
        .prop-type-int      {{ color: #4ade80 !important; }}   /* green   – int32 / int64 */
        .prop-type-float    {{ color: #fb923c !important; }}   /* orange  – float32 / float64 */
        .prop-type-boolean  {{ color: #a78bfa !important; }}   /* violet  – boolean */
        .prop-type-datetime {{ color: #f472b6 !important; }}   /* pink    – timestamp / date */
        .prop-type-json     {{ color: #facc15 !important; }}   /* yellow  – json */
        .prop-type-special  {{ color: #2dd4bf !important; }}   /* teal    – timeseries / file / sequence */
        .prop-type-node     {{ color: #94a3b8 !important; }}   /* slate   – direct_relation */
        .prop-type-relation {{ color: #4ade80 !important; }}   /* green   – relations (→ other views) */
        .prop-card {{ color: var(--text-muted); white-space: nowrap; }}
        .prop-desc {{ color: var(--text-secondary); }}
        .type-name {{ font-weight: 600; }}
        .type-code {{ opacity: 0.7; font-size: 0.6rem; display: block; }}
        
        .prop-sections {{ display: flex; flex-direction: column; gap: 0.5rem; }}
        .prop-section {{
            background: var(--bg-primary);
            border-radius: 6px;
            padding: 0.5rem;
            border: 1px solid var(--border-color);
        }}
        .prop-section .section-title {{ 
            font-size: 0.75rem;
            padding: 0.3rem 0.5rem;
            margin-bottom: 0.3rem;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border-color);
        }}
        .own-section .section-title {{ color: var(--accent-gold); }}
        .inherited-section .section-title {{ color: var(--text-muted); }}
        
        /* ER Diagrams */
        .diagram-level {{
            font-size: 1.3rem;
            color: var(--accent-gold);
            margin: 2rem 0 0.5rem 0;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border-color);
        }}
        .diagram-level:first-child {{
            margin-top: 0;
            padding-top: 0;
            border-top: none;
        }}
        .level-desc {{
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-bottom: 1rem;
        }}
        
        .er-diagram-box {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            overflow-x: auto;
        }}
        .er-diagram-box h3 {{ margin-bottom: 0.25rem; color: var(--text-primary); font-size: 1.1rem; }}
        .diagram-desc {{ color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem; }}
        
        .mermaid-source {{ display: none; }}
        .mermaid-rendered {{ 
            text-align: center; 
            background: var(--bg-primary); 
            border-radius: 6px; 
            padding: 0.5rem;
            overflow: hidden;
            height: 650px;
            position: relative;
        }}
        .mermaid-rendered svg {{ 
            display: block;
            margin: 0 auto;
        }}
        /* Brighter, thicker edges so they're readable on dark background */
        .mermaid-rendered svg .edgePath .path {{
            stroke: rgba(255, 255, 255, 0.9) !important;
            stroke-width: 2.5px !important;
        }}
        .mermaid-rendered svg .edgePath marker path,
        .mermaid-rendered svg .arrowheadPath {{
            fill: rgba(255, 255, 255, 0.9) !important;
            stroke: none !important;
        }}
        .mermaid-rendered svg .edgeLabel .label {{
            color: #f1f5f9 !important;
            font-weight: 500;
        }}
        .mermaid-rendered svg .edgeLabel rect {{
            fill: #1e293b !important;
            opacity: 0.9;
        }}
        /* Light-mode overrides: dark text, no shadow box, dark edge lines */
        [data-theme="light"] .mermaid-rendered svg .edgeLabel .label {{
            color: var(--text-primary) !important;
        }}
        [data-theme="light"] .mermaid-rendered svg .edgeLabel rect {{
            fill: transparent !important;
            opacity: 0 !important;
        }}
        [data-theme="light"] .mermaid-rendered svg .edgePath .path {{
            stroke: rgba(30, 41, 59, 0.8) !important;
        }}
        [data-theme="light"] .mermaid-rendered svg .edgePath marker path,
        [data-theme="light"] .mermaid-rendered svg .arrowheadPath {{
            fill: rgba(30, 41, 59, 0.8) !important;
        }}
        /* Dashed edges (implements) slightly dimmer to distinguish from data edges */
        .mermaid-rendered svg .edgePath path[style*="dashed"] {{
            stroke: rgba(148, 163, 184, 0.7) !important;
            stroke-width: 1.5px !important;
        }}
        .er-diagram-box {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            overflow: auto;
        }}
        /* Collapsible diagram cards */
        .er-diagram-box h3 {{ cursor: pointer; user-select: none; }}
        .er-diagram-box h3::before {{ content: '▼ '; font-size: 0.75em; color: var(--text-muted); }}
        .er-diagram-box.collapsed h3::before {{ content: '▶ '; }}
        .er-diagram-box.collapsed .mermaid-rendered,
        .er-diagram-box.collapsed .diagram-desc {{ display: none; }}
        /* ER section controls bar */
        .er-section-controls {{
            display: flex; align-items: center; gap: 0.75rem;
            margin-bottom: 1.25rem;
        }}
        .er-toggle-btn {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.82rem;
        }}
        .er-toggle-btn:hover {{ border-color: var(--accent-gold); color: var(--accent-gold); }}
        
        /* Clickable diagram nodes */
        .clickable-node {{
            cursor: pointer !important;
            transition: all 0.2s ease;
        }}
        .clickable-node:hover {{
            filter: brightness(1.3);
        }}
        .clickable-node:hover rect,
        .clickable-node:hover polygon,
        .clickable-node:hover circle {{
            stroke: var(--accent-gold) !important;
            stroke-width: 3px !important;
        }}
        

        /* Diagram fullscreen overlay */
        .diag-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: var(--bg-primary);
            z-index: 2000;
            flex-direction: column;
        }}
        .diag-overlay.active {{ display: flex; }}
        .diag-overlay-header {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.75rem 1.25rem;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            flex-shrink: 0;
        }}
        .diag-overlay-title {{ flex: 1; font-weight: 600; color: var(--accent-gold); font-size: 1rem; }}
        .diag-overlay-close {{
            background: var(--accent-gold);
            border: none;
            color: var(--bg-primary);
            width: 32px; height: 32px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.1rem;
            line-height: 32px;
        }}
        .diag-overlay-body {{
            flex: 1;
            position: relative;
            overflow: hidden;
            background: var(--bg-primary);
        }}
        .diag-overlay-body svg {{ width: 100%; height: 100%; display: block; }}
        .btn-diagram-expand {{
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            margin-left: auto;
            flex-shrink: 0;
        }}
        .btn-diagram-expand:hover {{ border-color: var(--accent-gold); color: var(--accent-gold); }}
                /* Modal */
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            z-index: 3000;
            overflow-y: auto;
            padding: 2rem;
        }}
        .modal-overlay.active {{ display: block; }}
        .modal-content {{
            background: var(--bg-card);
            border: 1px solid var(--accent-gold);
            border-radius: 12px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .modal-header {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1.5rem;
            border-bottom: 1px solid var(--border-color);
        }}
        .modal-title {{ font-size: 1.25rem; font-weight: 600; flex: 1; }}
        .modal-close {{
            background: var(--accent-gold);
            border: none;
            color: var(--bg-primary);
            width: 36px; height: 36px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.25rem;
        }}
        .modal-body {{ padding: 1.5rem; }}
        /* Modal property table - optimized column widths for wider view */
        .modal-body .prop-table {{ table-layout: fixed; }}
        .modal-body .prop-table th:nth-child(1) {{ width: 18%; }}
        .modal-body .prop-table th:nth-child(2) {{ width: 16%; }}
        .modal-body .prop-table th:nth-child(3) {{ width: 16%; }}
        .modal-body .prop-table th:nth-child(4) {{ width: 8%; }}
        .modal-body .prop-table th:nth-child(5) {{ width: 42%; }}
        
        /* Category colors - Industry domain-based */
        .cat-location-geography {{ background: linear-gradient(135deg, #10b981, #059669); }}
        .cat-wells-completions {{ background: linear-gradient(135deg, #8b5cf6, #7c3aed); }}
        .cat-subsurface-reservoir {{ background: linear-gradient(135deg, #a855f7, #9333ea); }}
        .cat-rotating-equipment {{ background: linear-gradient(135deg, #ef4444, #dc2626); }}
        .cat-static-equipment {{ background: linear-gradient(135deg, #f97316, #ea580c); }}
        .cat-piping-valves {{ background: linear-gradient(135deg, #84cc16, #65a30d); }}
        .cat-electrical-equipment {{ background: linear-gradient(135deg, #06b6d4, #0891b2); }}
        .cat-instrumentation-control {{ background: linear-gradient(135deg, #3b82f6, #2563eb); }}
        .cat-tags-functional-locations {{ background: linear-gradient(135deg, #6366f1, #4f46e5); }}
        .cat-timeseries-measurements {{ background: linear-gradient(135deg, #14b8a6, #0d9488); }}
        .cat-activities-work {{ background: linear-gradient(135deg, #eab308, #ca8a04); }}
        .cat-documents-files {{ background: linear-gradient(135deg, #ec4899, #db2777); }}
        .cat-commercial-procurement {{ background: linear-gradient(135deg, #f43f5e, #be185d); }}
        .cat-epc-project {{ background: linear-gradient(135deg, #d946ef, #c026d3); }}
        .cat-reference-classification {{ background: linear-gradient(135deg, #818cf8, #6366f1); }}
        .cat-organizational {{ background: linear-gradient(135deg, #64748b, #475569); }}
        .cat-3d-spatial {{ background: linear-gradient(135deg, #f59e0b, #d97706); }}
        .cat-cdm-core {{ background: linear-gradient(135deg, #3b82f6, #2563eb); }}
        .cat-cdm-features {{ background: linear-gradient(135deg, #10b981, #059669); }}
        .cat-idm-types {{ background: linear-gradient(135deg, #fb923c, #f97316); }}
        .cat-model-extensions {{ background: linear-gradient(135deg, #f59e0b, #d97706); }}
        
        /* ── Entity Hierarchy ── */
        .hierarchy-wrap {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
        }}
        .hierarchy-toolbar {{
            display: flex; align-items: center; gap: 0.65rem;
            margin-bottom: 0.75rem; flex-wrap: wrap;
            padding-bottom: 0.75rem; border-bottom: 1px solid var(--border-color);
        }}
        .hier-stats {{ color: var(--text-secondary); font-size: 0.82rem; margin-right: auto; }}
        .hier-ctrl-btn {{
            background: var(--bg-card); color: var(--text-primary);
            border: 1px solid var(--border-color); border-radius: 0.4rem;
            padding: 0.28rem 0.75rem; cursor: pointer; font-size: 0.8rem;
            transition: background 0.15s;
        }}
        .hier-ctrl-btn:hover {{ background: var(--accent-blue); color: #fff; }}
        .hier-filter-input {{
            background: var(--bg-card); border: 1px solid var(--border-color);
            border-radius: 0.4rem; padding: 0.28rem 0.75rem;
            color: var(--text-primary); font-size: 0.8rem; width: 220px; outline: none;
        }}
        .hier-filter-input:focus {{ border-color: var(--accent-blue); }}
        .hierarchy-legend {{
            display: flex; gap: 1.25rem; margin-bottom: 0.75rem;
            font-size: 0.78rem; color: var(--text-secondary); flex-wrap: wrap;
        }}
        .hier-legend-item {{ display: flex; align-items: center; gap: 0.3rem; }}
        .hier-root {{ list-style: none; padding-left: 0; margin: 0; }}
        .hier-children {{
            list-style: none; padding-left: 1.45rem; margin: 0;
            margin-left: 0.45rem;
            border-left: 2px solid rgba(96, 165, 250, 0.28);
            position: relative;
        }}
        .hier-node {{ margin: 0; position: relative; }}
        /* Horizontal connector from vertical guide to each node row */
        .hier-children > .hier-node > .hier-row::before {{
            content: '';
            position: absolute;
            left: -1.45rem;
            top: 50%;
            width: 1.15rem;
            height: 2px;
            background: rgba(96, 165, 250, 0.28);
            transform: translateY(-50%);
        }}
        .hier-row {{
            display: flex; align-items: center; gap: 0.3rem;
            padding: 0.13rem 0.3rem; border-radius: 0.22rem;
            position: relative;
        }}
        .hier-row:hover {{ background: rgba(255,255,255,0.04); }}
        .hier-toggle {{
            background: none; border: none; color: var(--text-muted);
            cursor: pointer; font-size: 0.65rem;
            width: 1.05rem; height: 1.05rem;
            display: flex; align-items: center; justify-content: center;
            padding: 0; flex-shrink: 0; border-radius: 0.2rem;
            transition: color 0.15s;
        }}
        .hier-toggle:hover {{ color: var(--text-primary); }}
        .hier-leaf-spacer {{ width: 1.05rem; flex-shrink: 0; display: inline-block; }}
        .hier-label {{
            font-size: 0.87rem; padding: 0.04rem 0.22rem;
            border-radius: 0.18rem; line-height: 1.45; user-select: none;
        }}
        .hier-label.hier-clickable {{ cursor: pointer; }}
        .hier-label.hier-clickable:hover {{ text-decoration: underline; opacity: 0.85; }}
        .hier-label.hier-cdm    {{ color: #60a5fa; }}
        .hier-label.hier-idm    {{ color: #fb923c; }}
        .hier-label.hier-domain {{ color: #4ade80; }}
        .hier-label.hier-other  {{ color: var(--text-secondary); }}
        .hier-cdm    {{ color: #60a5fa; }}
        .hier-idm    {{ color: #fb923c; }}
        .hier-domain {{ color: #4ade80; }}
        .hier-prop-badge {{
            background: rgba(255,255,255,0.07); color: var(--text-muted);
            font-size: 0.65rem; padding: 0.03rem 0.28rem;
            border-radius: 1rem; margin-left: 0.1rem; white-space: nowrap;
        }}
        .hier-kind-badge {{
            font-size: 0.6rem; padding: 0.03rem 0.26rem;
            border-radius: 0.22rem; font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.04em; margin-left: 0.15rem;
        }}
        .hier-badge-cdm {{ background: rgba(96,165,250,0.15);  color: #60a5fa; }}
        .hier-badge-idm {{ background: rgba(251,146,60,0.15);  color: #fb923c; }}
        .hier-hidden {{ display: none !important; }}

        footer {{
            text-align: center;
            padding: 2rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <header>
        <div class="theme-toggle">
            <span class="theme-icon">🌙</span>
            <label class="toggle-switch">
                <input type="checkbox" id="themeToggle">
                <span class="toggle-slider"></span>
            </label>
            <span class="theme-icon">☀️</span>
        </div>
        <h1>{model_name}</h1>
        <p class="model-id"><code>{model_subtitle}</code></p>
    </header>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value">{total_views}</div>
            <div class="stat-label">View Types</div>
        </div>
        <div class="stat">
            <div class="stat-value">{total_props}</div>
            <div class="stat-label">Properties</div>
        </div>
        <div class="stat">
            <div class="stat-value">{total_relations}</div>
            <div class="stat-label">Direct Relations</div>
        </div>
        <div class="search-dual">
            <div class="search-box">
                <div class="search-box-inner">
                    <span class="search-box-label">Search View Types</span>
                    <input type="text" class="search-input" id="viewSearchInput" placeholder="e.g. Asset, Equipment..." autocomplete="off">
                    <div class="search-filter" id="viewFilter"></div>
                </div>
                <div class="search-results" id="viewSearchResults"></div>
            </div>
            <div class="search-box">
                <div class="search-box-inner">
                    <span class="search-box-label">Search Properties</span>
                    <input type="text" class="search-input" id="propSearchInput" placeholder="e.g. name, description..." autocomplete="off">
                    <div class="search-filter" id="propFilter"></div>
                </div>
                <div class="search-results" id="propSearchResults"></div>
            </div>
            <div class="search-help">Search by name, description, or externalId. Type in one field to limit results of the other. Use <code>*</code> to see all results dependent on the other filter.</div>
        </div>
    </div>
    
    <nav class="nav-tabs">
        {''.join(nav_tabs)}
    </nav>
    
    <div class="container">
        <div id="overview" class="section active">
            <h2 class="section-title">Model Overview</h2>
            <p class="section-description">{description}</p>
            {overview_diagram}
        </div>
        
        {''.join(category_sections)}
        
        <div id="hierarchy" class="section">
            <h2 class="section-title">&#127960; Entity Hierarchy</h2>
            <p class="section-description">Entities organised by their <em>implements</em> (inheritance) relationships. Only CDM/IDM base types actually referenced by this model are shown. Click any entity label to view its details.</p>
            {hierarchy_html}
        </div>

        <div id="erdiagram" class="section">
            <h2 class="section-title">Entity-Relationship Diagrams</h2>
            <p class="section-description">Multi-level UML class diagrams for information modeling</p>
            <div class="er-section-controls">
                <button class="er-toggle-btn" id="er-toggle-btn" onclick="toggleAllERCards()">&#9660; Expand All</button>
            </div>
            {er_diagrams}
        </div>
    </div>
    
    <div class="diag-overlay" id="diag-overlay">
        <div class="diag-overlay-header">
            <span class="diag-overlay-title" id="diag-overlay-title">Diagram</span>
            <button class="diag-overlay-close" onclick="closeDiagOverlay()" title="Close">&times;</button>
        </div>
        <div class="diag-overlay-body" id="diag-overlay-body"></div>
    </div>
        <div class="modal-overlay" id="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-icon"></div>
                <div class="modal-title"></div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body"></div>
        </div>
    </div>
    
    <footer>
        <p>{model_name} | {model_subtitle} | Generated by NEAT html-doc</p>
    </footer>
    
    <script>
        // Node ID to View ID mapping for clickable diagrams
        var nodeMapping = {node_mapping_js};
        var hierExtraData = {hier_extra_js};
        
        mermaid.initialize({{ 
            startOnLoad: false,
            securityLevel: 'loose',
            theme: 'dark',
            themeVariables: {{
                primaryColor: '#3b82f6',
                primaryTextColor: '#f8fafc',
                primaryBorderColor: '#2d3f5f',
                lineColor: '#64748b',
                secondaryColor: '#1a2744',
                tertiaryColor: '#0f172a',
                background: '#0f172a',
                mainBkg: '#1a2744',
                nodeBorder: '#3b82f6',
                clusterBkg: 'transparent',
                clusterBorder: 'transparent',
                titleColor: '#f8fafc',
                edgeLabelBackground: 'transparent',
                textColor: '#f8fafc',
                fontSize: '13px',
                classText: '#f8fafc'
            }},
            flowchart: {{
                nodeSpacing: 12,
                rankSpacing: 22,
                curve: 'basis',
                htmlLabels: true,
                useMaxWidth: true,
                padding: 4
            }}
        }});
        
        // ── Hover edge highlighting ───────────────────────────────────────────
        // Strategy:
        //   FIRST call (inline diagram): geometric matching → annotate every edge
        //     path with data-eh-nodes="MermaidId1,MermaidId2" so the result
        //     survives cloneNode(true) into the pop-out.
        //   SECOND call (pop-out clone): reads annotations directly — no geometry,
        //     no coordinate-system issues from pan-zoom transforms.
        function addEdgeHighlighting(container) {{
            var svg = container.querySelector('svg');
            if (!svg) return;

            // ── shared helpers ──────────────────────────────────────────────
            function hasClass(el, name) {{
                return (' ' + (el.getAttribute('class') || '') + ' ').includes(' ' + name + ' ');
            }}
            function edgeGroupOf(path) {{
                var g = path.parentElement;
                for (var d = 0; g && g !== svg && d < 8; d++, g = g.parentElement) {{
                    var gid = g.id || '';
                    if (hasClass(g, 'edgePath')) return g;
                    if (hasClass(g, 'node') || hasClass(g, 'default') ||
                        gid.match(/^flowchart-/)) return null;
                    if (hasClass(g, 'edgePaths')) return path;
                }}
                return path;
            }}

            // ── node map (used in both modes) ───────────────────────────────
            var nodeMap = {{}};
            svg.querySelectorAll('g[id], g.node, g.default').forEach(function(g) {{
                var cls = ' ' + (g.getAttribute('class') || '') + ' ';
                if (cls.includes(' cluster ') || cls.includes(' clusters ') ||
                    cls.includes(' edgePaths ') || cls.includes(' edgeLabels ') ||
                    cls.includes(' edgePath ')) return;
                var nid = g.id || '';
                var m   = nid.match(/flowchart-(.+)-[0-9]+$/);
                var mId = m ? m[1] : null;
                if (!mId && nid && !nid.match(/^(root|background|classDefs|subGraphs|edgePaths|edgeLabels|clusters|mermaid|svg-pan-zoom)/)) {{
                    mId = nid;
                }}
                if (!mId || nodeMap[mId]) return;
                var shape = g.querySelector(':scope > rect, :scope > polygon, :scope > circle, :scope > ellipse');
                var hitEl = shape || g;
                var rect  = hitEl.getBoundingClientRect();
                if (rect.width < 1) return;
                nodeMap[mId] = {{ el: g, hitEl: hitEl }};
            }});
            var nodeKeys = Object.keys(nodeMap);
            if (!nodeKeys.length) {{ console.debug('[EdgeHL] no nodes found'); return; }}

            // ── wire hover handlers (shared by both modes) ──────────────────
            function wireHovers(nodeEdgeMap, allEdgeGroups) {{
                if (!allEdgeGroups.length) return;
                Object.keys(nodeEdgeMap).forEach(function(mId) {{
                    var entry = nodeMap[mId];
                    if (!entry) return;
                    var connected = nodeEdgeMap[mId];

                    entry.hitEl.addEventListener('mouseenter', function() {{
                        allEdgeGroups.forEach(function(grp) {{
                            if (connected.has(grp)) {{
                                grp.style.setProperty('opacity', '1', 'important');
                                var ps = grp.tagName.toLowerCase() === 'path'
                                    ? [grp] : Array.from(grp.querySelectorAll('path'));
                                ps.forEach(function(p) {{
                                    p.style.setProperty('stroke',       '#facc15', 'important');
                                    p.style.setProperty('stroke-width', '2.5px',   'important');
                                }});
                            }} else {{
                                grp.style.setProperty('opacity', '0.35', 'important');
                            }}
                        }});
                    }});

                    entry.hitEl.addEventListener('mouseleave', function() {{
                        allEdgeGroups.forEach(function(grp) {{
                            grp.style.removeProperty('opacity');
                            var ps = grp.tagName.toLowerCase() === 'path'
                                ? [grp] : Array.from(grp.querySelectorAll('path'));
                            ps.forEach(function(p) {{
                                p.style.removeProperty('stroke');
                                p.style.removeProperty('stroke-width');
                            }});
                        }});
                    }});
                }});
            }}

            // ── MODE A: annotation fast-path (pop-out clone) ────────────────
            // Paths annotated in the original inline pass survive cloneNode(true).
            // No geometry or coordinate transforms needed.
            var annotated = Array.from(svg.querySelectorAll('path[data-eh-nodes]'));
            if (annotated.length) {{
                var nemA = {{}}, egrA = [], seenA = new Set();
                annotated.forEach(function(path) {{
                    var ids = (path.getAttribute('data-eh-nodes') || '').split(',').filter(Boolean);
                    if (!ids.length) return;
                    var grp = edgeGroupOf(path) || path;
                    if (!seenA.has(grp)) {{ seenA.add(grp); egrA.push(grp); }}
                    ids.forEach(function(id) {{
                        if (!nemA[id]) nemA[id] = new Set();
                        nemA[id].add(grp);
                    }});
                }});
                console.debug('[EdgeHL] annotation mode – groups:', egrA.length, 'nodes:', Object.keys(nemA).length);
                wireHovers(nemA, egrA);
                return;
            }}

            // ── MODE B: geometric matching (first call on inline diagram) ───
            var vpEl  = svg.querySelector('#svg-pan-zoom-viewport') || svg;
            var ctm   = vpEl.getScreenCTM() || svg.getScreenCTM();
            function toScreen(pt) {{
                if (!ctm) return pt;
                var sp = svg.createSVGPoint();
                sp.x = pt.x; sp.y = pt.y;
                return sp.matrixTransform(ctm);
            }}

            // Collect node rects (needed only for matching, not for hover)
            var nodeRects = {{}};
            svg.querySelectorAll('g[id], g.node, g.default').forEach(function(g) {{
                var cls = ' ' + (g.getAttribute('class') || '') + ' ';
                if (cls.includes(' cluster ') || cls.includes(' edgePaths ') ||
                    cls.includes(' edgeLabels ') || cls.includes(' edgePath ')) return;
                var nid = g.id || '';
                var m   = nid.match(/flowchart-(.+)-[0-9]+$/);
                var mId = m ? m[1] : (nid && !nid.match(/^(root|background|classDefs|subGraphs|edgePaths|edgeLabels|clusters|mermaid|svg-pan-zoom)/) ? nid : null);
                if (!mId || nodeRects[mId]) return;
                var shape = g.querySelector(':scope > rect, :scope > polygon, :scope > circle, :scope > ellipse');
                var r = (shape || g).getBoundingClientRect();
                if (r.width > 0) nodeRects[mId] = r;
            }});
            var rectKeys = Object.keys(nodeRects);

            var PAD = 10;
            function nodeForPoint(sx, sy) {{
                var best = null, bestDist = PAD;
                for (var i = 0; i < rectKeys.length; i++) {{
                    var r = nodeRects[rectKeys[i]];
                    if (sx < r.left - PAD || sx > r.right  + PAD ||
                        sy < r.top  - PAD || sy > r.bottom + PAD) continue;
                    var dx = Math.max(r.left - sx, 0, sx - r.right);
                    var dy = Math.max(r.top  - sy, 0, sy - r.bottom);
                    var dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist <= bestDist) {{ bestDist = dist; best = rectKeys[i]; }}
                }}
                return best;
            }}

            // Group paths by edgePath ancestor
            var edgeGroupMap = new Map();
            svg.querySelectorAll('path').forEach(function(path) {{
                if (path.closest('marker')) return;
                if ((path.getAttribute('d') || '').length < 10) return;
                // Skip invisible layout/spine edges (~~~ links have no arrowhead marker)
                var me = path.getAttribute('marker-end') || '';
                var ms = path.getAttribute('marker-start') || '';
                if (!me && !ms) {{
                    // Also check parent <g> for marker attributes (Mermaid sometimes puts them on the group)
                    var pg = path.parentElement;
                    me = (pg && pg.getAttribute('marker-end')) || '';
                    ms = (pg && pg.getAttribute('marker-start')) || '';
                    if (!me && !ms) return;
                }}
                var grp = edgeGroupOf(path);
                if (!grp) return;
                if (!edgeGroupMap.has(grp)) edgeGroupMap.set(grp, new Set());
                edgeGroupMap.get(grp).add(path);
            }});

            var nemB = {{}}, egrB = [];
            edgeGroupMap.forEach(function(paths, grp) {{
                var src = null, tgt = null;
                paths.forEach(function(path) {{
                    try {{
                        var len = path.getTotalLength();
                        if (len < 5) return;
                        if (!src) {{ var p0 = toScreen(path.getPointAtLength(0));   src = nodeForPoint(p0.x, p0.y); }}
                        if (!tgt) {{ var p1 = toScreen(path.getPointAtLength(len)); tgt = nodeForPoint(p1.x, p1.y); }}
                    }} catch(e) {{}}
                }});
                if (!src && !tgt) return;
                egrB.push(grp);
                var connIds = [];
                [src, tgt].forEach(function(id) {{
                    if (!id) return;
                    connIds.push(id);
                    if (!nemB[id]) nemB[id] = new Set();
                    nemB[id].add(grp);
                }});
                // Annotate every path in this group so the pop-out can reuse results
                var pathsToAnnotate = grp.tagName.toLowerCase() === 'path'
                    ? [grp] : Array.from(grp.querySelectorAll('path'));
                pathsToAnnotate.forEach(function(p) {{
                    p.setAttribute('data-eh-nodes', connIds.join(','));
                }});
            }});

            console.debug('[EdgeHL] geo mode – matched:', egrB.length, 'nodes wired:', Object.keys(nemB).length);
            wireHovers(nemB, egrB);
        }}

        // ── Helper: init svgPanZoom, never zooming small content beyond 100% ─
        function initPanZoom(svgEl, container, opts) {{
            var cw = container.clientWidth  || 800;
            var ch = container.clientHeight || 650;
            svgEl.removeAttribute('width');
            svgEl.removeAttribute('height');
            svgEl.style.removeProperty('max-width');
            svgEl.setAttribute('width',  cw);
            svgEl.setAttribute('height', ch);
            svgEl.style.width  = cw + 'px';
            svgEl.style.height = ch + 'px';

            // Read the SVG viewBox to know the natural content size
            var vbStr = svgEl.getAttribute('viewBox') || '';
            var vbP   = vbStr.trim().split(/[\s,]+/);
            var vbW   = parseFloat(vbP[2]) || cw;
            var vbH   = parseFloat(vbP[3]) || ch;

            var pz = svgPanZoom(svgEl, Object.assign({{
                zoomEnabled: true, controlIconsEnabled: true,
                fit: true, center: true, minZoom: 0.02, maxZoom: 30
            }}, opts || {{}}));

            // svgPanZoom normalises the fitted state to zoom=1.0 internally.
            // fitRatio = how much the viewBox content was scaled to fill the container.
            // If fitRatio > 1 the content is SMALLER than the container — it was zoomed in.
            // Un-zoom it back: in svgPanZoom's scale, natural-size = 1/fitRatio.
            var fitRatio = Math.min(cw / vbW, ch / vbH);
            if (fitRatio > 1) {{
                pz.zoom(1.0 / fitRatio);
                pz.center();
            }}
            return pz;
        }}

        // Make diagram nodes clickable
        function makeNodesClickable(container) {{
            const svg = container.querySelector('svg');
            if (!svg) return;
            
            // Collect all g elements that could be nodes (with id OR with .node class)
            const allGroups = svg.querySelectorAll('g[id], g.node, g.default');
            
            function findViewId(nodeId, allText) {{
                // 1. Direct node ID match against mapping keys
                if (nodeMapping[nodeId]) return nodeMapping[nodeId];
                
                // 2. Extract name from flowchart ID pattern (flowchart-Name-N)
                var flowMatch = nodeId.match(/flowchart-([^-]+)/);
                if (flowMatch && nodeMapping[flowMatch[1]]) return nodeMapping[flowMatch[1]];
                
                // 3. Extract name from class diagram ID pattern (classId-Name-N)
                var classMatch = nodeId.match(/classId-([^-]+)/);
                if (classMatch && nodeMapping[classMatch[1]]) return nodeMapping[classMatch[1]];
                
                // 4. Check if node ID contains any mapping key
                for (var key in nodeMapping) {{
                    if (key.length >= 3 && nodeId.includes(key)) return nodeMapping[key];
                }}
                
                // 5. Exact text match against mapping keys (catches display names)
                if (allText && nodeMapping[allText]) return nodeMapping[allText];
                
                // 6. Text content starts with or equals a mapping key
                if (allText) {{
                    for (var key in nodeMapping) {{
                        if (key.length >= 3 && (allText === key || allText.startsWith(key))) {{
                            return nodeMapping[key];
                        }}
                    }}
                }}
                
                return null;
            }}
            
            function makeClickable(el, viewId) {{
                if (el.classList.contains('clickable-node')) return;
                var card = document.querySelector('.card[data-view-id="' + viewId + '"]') ||
                           document.querySelector('.card[data-node-id="' + viewId + '"]');
                if (!card) return;
                el.style.cursor = 'pointer';
                el.classList.add('clickable-node');
                el.addEventListener('click', function(e) {{
                    e.stopPropagation();
                    e.preventDefault();
                    openModalFromDiagram(viewId);
                }});
            }}
            
            allGroups.forEach(function(node) {{
                if (node.classList.contains('clickable-node')) return;
                
                var nodeId = node.id || '';
                var textEls = node.querySelectorAll('text, tspan');
                var allText = '';
                textEls.forEach(function(t) {{ allText += ' ' + t.textContent; }});
                allText = allText.trim();
                
                var viewId = findViewId(nodeId, allText);
                if (viewId) makeClickable(node, viewId);
            }});
            
            // Fallback: find text elements and make their parent nodes clickable
            svg.querySelectorAll('text').forEach(function(textEl) {{
                var text = textEl.textContent.trim();
                if (!text || text.length < 2) return;
                
                var viewId = nodeMapping[text];
                if (!viewId) {{
                    for (var key in nodeMapping) {{
                        if (text === key) {{ viewId = nodeMapping[key]; break; }}
                    }}
                }}
                
                if (viewId) {{
                    var parent = textEl.closest('g.node') || textEl.closest('g[id]') || textEl.closest('g.default');
                    if (!parent) {{
                        parent = textEl.parentElement;
                        while (parent && parent.tagName === 'g' && !parent.id && !parent.classList.contains('node')) {{
                            parent = parent.parentElement;
                        }}
                    }}
                    if (parent && parent.tagName === 'g') {{
                        makeClickable(parent, viewId);
                    }}
                }}
            }});
        }}
        
        // Open modal from diagram click, returning to source section on close
        function openModalFromDiagram(viewId) {{
            var card = document.querySelector('.card[data-view-id="' + viewId + '"]') ||
                       document.querySelector('.card[data-node-id="' + viewId + '"]');
            if (!card) {{
                console.log('No card found for view:', viewId);
                return;
            }}
            var header = card.querySelector('.card-header');
            var icon = header.querySelector('.card-icon').innerHTML;
            var title = card.querySelector('.card-title').innerHTML;
            var propsHtml = card.querySelector('.card-properties').innerHTML;
            document.querySelector('.modal-icon').innerHTML = icon;
            document.querySelector('.modal-title').innerHTML = title;
            document.querySelector('.modal-body').innerHTML = propsHtml;
            var modal = document.getElementById('modal');
            modal.classList.add('active');
            // Remember which section was active so we can return to it
            var activeSection = document.querySelector('.section.active');
            modal.setAttribute('data-source-section', activeSection ? activeSection.id : '');
            document.body.style.overflow = 'hidden';
        }}
        

        var _diagPanZoom = null;

        // ── Overlay click: bypass svgPanZoom interception via pointerup on overlayBody ──
        (function() {{
            var _ptDown = null;
            var overlayBody = document.getElementById('diag-overlay-body');
            overlayBody.addEventListener('pointerdown', function(e) {{
                _ptDown = {{ x: e.clientX, y: e.clientY }};
            }});
            overlayBody.addEventListener('pointerup', function(e) {{
                if (!_ptDown) return;
                var dx = e.clientX - _ptDown.x, dy = e.clientY - _ptDown.y;
                _ptDown = null;
                // Only treat as click if pointer barely moved (not a pan)
                if (Math.sqrt(dx*dx + dy*dy) > 6) return;
                // Walk up from the element under cursor to find a clickable node group
                var el = document.elementFromPoint(e.clientX, e.clientY);
                while (el && el !== overlayBody) {{
                    if (el.classList && (el.classList.contains('clickable-node') ||
                        el.classList.contains('node') || el.classList.contains('default'))) {{
                        var vid = el._diagramViewId;
                        if (!vid) {{
                            // Try to resolve from node mapping via text content
                            var txt = '';
                            el.querySelectorAll('text,tspan').forEach(function(t) {{ txt += ' ' + t.textContent; }});
                            txt = txt.trim();
                            vid = nodeMapping[txt];
                            if (!vid && el.id) {{
                                var fm = el.id.match(/flowchart-([^-]+)/);
                                if (fm) vid = nodeMapping[fm[1]];
                            }}
                        }}
                        if (vid) {{ openModalFromDiagram(vid); return; }}
                    }}
                    el = el.parentElement;
                }}
            }});
        }})();

        function expandDiagram(box) {{
            var rendered = box.querySelector('.mermaid-rendered');
            if (!rendered) return;
            var svgEl = rendered.querySelector('svg');
            if (!svgEl) return;
            var h3 = box.querySelector('h3');
            var titleText = h3 ? h3.textContent.replace(/\u26F6.*/g, '').trim() : 'Diagram';
            document.getElementById('diag-overlay-title').textContent = titleText;
            var overlayBody = document.getElementById('diag-overlay-body');
            overlayBody.innerHTML = '';
            var clone = svgEl.cloneNode(true);
            clone.removeAttribute('width'); clone.removeAttribute('height');
            var oldCtrl = clone.querySelector('#svg-pan-zoom-controls');
            if (oldCtrl) oldCtrl.parentNode.removeChild(oldCtrl);
            // Strip any frozen hover-highlight styles baked into the clone
            // (the inline diagram may have active highlights when pop-out opens).
            clone.querySelectorAll('path').forEach(function(p) {{
                p.style.removeProperty('stroke');
                p.style.removeProperty('stroke-width');
                p.style.removeProperty('opacity');
            }});
            clone.querySelectorAll('g').forEach(function(g) {{
                g.style.removeProperty('opacity');
            }});
            clone.style.display = 'block';
            overlayBody.appendChild(clone);
            // Show overlay first so the container has real pixel dimensions
            document.getElementById('diag-overlay').classList.add('active');
            document.body.style.overflow = 'hidden';
            requestAnimationFrame(function() {{
                if (_diagPanZoom) {{ try {{ _diagPanZoom.destroy(); }} catch(e) {{}} _diagPanZoom = null; }}
                if (typeof svgPanZoom !== 'undefined') {{
                    try {{ _diagPanZoom = initPanZoom(clone, overlayBody); }}
                    catch(e) {{ console.warn('overlay panZoom', e); }}
                }}
                // Store viewId on each node group so the pointerup handler can find it
                clone.querySelectorAll('g.node, g.default, g[id]').forEach(function(g) {{
                    var nodeId = g.id || '';
                    var textContent = '';
                    g.querySelectorAll('text,tspan').forEach(function(t) {{ textContent += ' ' + t.textContent; }});
                    textContent = textContent.trim();
                    var vid = null;
                    if (nodeMapping[nodeId]) vid = nodeMapping[nodeId];
                    var fm = nodeId.match(/flowchart-([^-]+)/);
                    if (!vid && fm && nodeMapping[fm[1]]) vid = nodeMapping[fm[1]];
                    if (!vid && textContent && nodeMapping[textContent]) vid = nodeMapping[textContent];
                    if (!vid) {{
                        for (var k in nodeMapping) {{
                            if (k.length >= 3 && nodeId.includes(k)) {{ vid = nodeMapping[k]; break; }}
                        }}
                    }}
                    if (vid) g._diagramViewId = vid;
                }});
                // Lazy-init edge highlighting on the pop-out: wait for the user's
                // first mousemove so that all pan-zoom transforms have fully settled
                // and no false trigger fires from cursor position at open time.
                var _hlReady = false;
                overlayBody.addEventListener('mousemove', function _initHL() {{
                    if (_hlReady) return;
                    _hlReady = true;
                    overlayBody.removeEventListener('mousemove', _initHL);
                    addEdgeHighlighting(overlayBody);
                }});
            }});
        }}

        function closeDiagOverlay() {{
            if (_diagPanZoom) {{ try {{ _diagPanZoom.destroy(); }} catch(e) {{}} _diagPanZoom = null; }}
            document.getElementById('diag-overlay-body').innerHTML = '';
            document.getElementById('diag-overlay').classList.remove('active');
            document.body.style.overflow = '';
        }}

        function addExpandButton(container) {{
            var box = container.closest('.overview-diagram, .er-diagram-box');
            if (!box || box.querySelector('.btn-diagram-expand')) return;
            var h3 = box.querySelector('h3');
            if (!h3) return;
            h3.style.display = 'flex';
            h3.style.alignItems = 'center';
            h3.style.gap = '0.5rem';
            var btn = document.createElement('button');
            btn.className = 'btn-diagram-expand';
            btn.title = 'Open full screen';
            btn.innerHTML = '&#x26F6;';
            btn.onclick = function(e) {{ e.stopPropagation(); expandDiagram(box); }};
            h3.appendChild(btn);
        }}


                        document.addEventListener('DOMContentLoaded', async function() {{
            const overviewDiagrams = document.querySelectorAll('.overview-diagram .mermaid-source');
            for (const el of overviewDiagrams) {{
                const id = 'o-' + Math.random().toString(36).substr(2, 9);
                try {{
                    const {{ svg }} = await mermaid.render(id, el.textContent);
                    const div = document.createElement('div');
                    div.innerHTML = svg;
                    div.className = 'mermaid-rendered';
                    el.parentNode.replaceChild(div, el);
                    makeNodesClickable(div);
                    addEdgeHighlighting(div);
                    if (typeof svgPanZoom !== 'undefined') {{
                        var svgEl = div.querySelector('svg');
                        if (svgEl) initPanZoom(svgEl, div);
                    }}
                    addExpandButton(div);
                }} catch (e) {{
                    console.error('Diagram error:', e);
                }}
            }}
        }});
        
        var erRendered = false;
        
        function showSection(sectionId) {{
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            document.getElementById(sectionId).classList.add('active');
            event.target.classList.add('active');
            
            if (sectionId === 'erdiagram' && !erRendered) {{
                setTimeout(async function() {{
                    const erDiagrams = document.querySelectorAll('#erdiagram .mermaid-source');
                    for (const el of erDiagrams) {{
                        const id = 'e-' + Math.random().toString(36).substr(2, 9);
                        try {{
                            const {{ svg }} = await mermaid.render(id, el.textContent);
                            const div = document.createElement('div');
                            div.innerHTML = svg;
                            div.className = 'mermaid-rendered';
                            el.parentNode.replaceChild(div, el);
                            makeNodesClickable(div);
                            addEdgeHighlighting(div);
                            if (typeof svgPanZoom !== 'undefined') {{
                                var svgEl2 = div.querySelector('svg');
                                if (svgEl2) initPanZoom(svgEl2, div);
                            }}
                            addExpandButton(div);
                        }} catch (e) {{
                            console.error('ER error:', e);
                            el.style.display = 'block';
                            el.style.color = '#ef4444';
                            el.style.whiteSpace = 'pre-wrap';
                        }}
                    }}
                    erRendered = true;
                    // Wire click-to-collapse on each card h3, then start all collapsed
                    wireERCardToggle();
                    document.querySelectorAll('#erdiagram .er-diagram-box').forEach(function(b) {{
                        b.classList.add('collapsed');
                    }});
                    updateERToggleBtn();
                }}, 100);
            }}
        }}
        
        // ── Diagram card collapse / expand ────────────────────────────────────
        function toggleERCard(box) {{
            box.classList.toggle('collapsed');
            updateERToggleBtn();
        }}

        function updateERToggleBtn() {{
            var btn = document.getElementById('er-toggle-btn');
            if (!btn) return;
            var boxes = document.querySelectorAll('#erdiagram .er-diagram-box');
            var anyOpen = Array.from(boxes).some(function(b) {{ return !b.classList.contains('collapsed'); }});
            if (anyOpen) {{
                btn.innerHTML = '&#9651; Collapse All';
            }} else {{
                btn.innerHTML = '&#9660; Expand All';
            }}
        }}

        function toggleAllERCards() {{
            var boxes = document.querySelectorAll('#erdiagram .er-diagram-box');
            var anyOpen = Array.from(boxes).some(function(b) {{ return !b.classList.contains('collapsed'); }});
            boxes.forEach(function(b) {{
                if (anyOpen) b.classList.add('collapsed');
                else b.classList.remove('collapsed');
            }});
            updateERToggleBtn();
        }}

        function wireERCardToggle() {{
            document.querySelectorAll('#erdiagram .er-diagram-box').forEach(function(box) {{
                var h3 = box.querySelector('h3');
                if (h3 && !h3._toggleWired) {{
                    h3._toggleWired = true;
                    h3.addEventListener('click', function(e) {{
                        // Don't toggle if the expand-fullscreen button was clicked
                        if (e.target.closest('.btn-diagram-expand')) return;
                        toggleERCard(box);
                    }});
                }}
            }});
        }}

        function toggleCard(card) {{ card.classList.toggle('expanded'); }}
        
        function openModal(viewId) {{
            var card = document.querySelector('.card[data-view-id="' + viewId + '"]') ||
                       document.querySelector('.card[data-node-id="' + viewId + '"]');
            if (!card) return;
            var header = card.querySelector('.card-header');
            var icon = header.querySelector('.card-icon').innerHTML;
            var title = card.querySelector('.card-title').innerHTML;
            var propsHtml = card.querySelector('.card-properties').innerHTML;
            document.querySelector('.modal-icon').innerHTML = icon;
            document.querySelector('.modal-title').innerHTML = title;
            document.querySelector('.modal-body').innerHTML = propsHtml;
            document.getElementById('modal').classList.add('active');
            document.body.style.overflow = 'hidden';
        }}
        
        // ── Class Hierarchy ──────────────────────────────────────────────
        function hierClick(viewId) {{
            // Try to open the full entity card modal first
            var card = document.querySelector('.card[data-view-id="' + viewId + '"]');
            if (card) {{
                openModal(viewId);
                return;
            }}
            // Fallback: show a lightweight info popup from hierExtraData
            var data = hierExtraData[viewId];
            if (!data) return;
            var kindLabel = data.kind === 'idm' ? 'IDM' : 'CDM';
            var kindColor = data.kind === 'idm' ? '#fb923c' : '#60a5fa';
            var propsLine = data.props > 0 ? '<p style="margin:0.5rem 0 0;color:#94a3b8;font-size:0.82rem;">'
                            + data.props + ' properties defined</p>' : '';
            var descHtml = data.desc
                ? '<p style="margin:0.5rem 0 0;color:#cbd5e1;font-size:0.85rem;">' + data.desc + '</p>'
                : '';
            document.querySelector('.modal-icon').innerHTML =
                '<span style="font-size:1.4rem;background:rgba(255,255,255,0.08);padding:0.35rem 0.6rem;'
                + 'border-radius:0.4rem;">'
                + (data.kind === 'idm' ? '&#128310;' : '&#128309;') + '</span>';
            document.querySelector('.modal-title').innerHTML =
                '<span style="color:' + kindColor + ';">' + data.name + '</span>'
                + ' <span style="font-size:0.65rem;background:rgba(255,255,255,0.1);padding:0.1rem 0.4rem;'
                + 'border-radius:0.3rem;color:' + kindColor + ';">' + kindLabel + '</span>';
            document.querySelector('.modal-body').innerHTML =
                '<div style="padding:0.5rem 0;">'
                + '<p style="margin:0;color:#94a3b8;font-size:0.8rem;font-family:monospace;">' + viewId + '</p>'
                + descHtml + propsLine
                + '<p style="margin:1rem 0 0;color:#64748b;font-size:0.78rem;font-style:italic;">'
                + 'Base type \u2013 not a direct member of this data model.</p>'
                + '</div>';
            document.getElementById('modal').classList.add('active');
            document.body.style.overflow = 'hidden';
        }}

        function hierToggle(btn) {{
            var li = btn.closest('.hier-node');
            var ch = li ? li.querySelector('.hier-children') : null;
            if (!ch) return;
            var open = ch.style.display !== 'none';
            ch.style.display = open ? 'none' : '';
            btn.innerHTML = open ? '&#9658;' : '&#9660;';
        }}

        function hierExpandAll() {{
            document.querySelectorAll('#hierarchy .hier-children').forEach(function(el) {{
                el.style.display = '';
            }});
            document.querySelectorAll('#hierarchy .hier-toggle').forEach(function(b) {{
                b.innerHTML = '&#9660;';
            }});
        }}

        function hierCollapseAll() {{
            document.querySelectorAll('#hierarchy .hier-children').forEach(function(el) {{
                el.style.display = 'none';
            }});
            document.querySelectorAll('#hierarchy .hier-toggle').forEach(function(b) {{
                b.innerHTML = '&#9658;';
            }});
        }}

        var _hierTimer = null;
        function hierFilter(query) {{
            clearTimeout(_hierTimer);
            _hierTimer = setTimeout(function() {{
                var q = (query || '').toLowerCase().trim();
                var sec = document.getElementById('hierarchy');
                if (!sec) return;
                if (!q) {{
                    sec.querySelectorAll('.hier-node').forEach(function(n) {{
                        n.classList.remove('hier-hidden');
                    }});
                    return;
                }}
                sec.querySelectorAll('.hier-node').forEach(function(n) {{
                    n.classList.add('hier-hidden');
                }});
                sec.querySelectorAll('.hier-label').forEach(function(lbl) {{
                    if (lbl.textContent.toLowerCase().includes(q)) {{
                        var el = lbl.closest('.hier-node');
                        while (el && el.classList.contains('hier-node')) {{
                            el.classList.remove('hier-hidden');
                            var pUl = el.parentElement;
                            if (pUl) {{ pUl.style.display = ''; }}
                            el = pUl ? pUl.closest('.hier-node') : null;
                        }}
                    }}
                }});
            }}, 180);
        }}
        // ── End Class Hierarchy ────────────────────────────────────────────

        function closeModal() {{
            var modal = document.getElementById('modal');
            var sourceSection = modal.getAttribute('data-source-section');
            modal.classList.remove('active');
            modal.removeAttribute('data-source-section');
            // Keep overflow hidden if the diagram overlay is still open
            var diagOverlayOpen = document.getElementById('diag-overlay').classList.contains('active');
            document.body.style.overflow = diagOverlayOpen ? 'hidden' : '';
            
            // Return to the section the modal was opened from
            if (sourceSection) {{
                var target = document.getElementById(sourceSection);
                if (target && !target.classList.contains('active')) {{
                    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
                    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                    target.classList.add('active');
                    document.querySelectorAll('.nav-tab').forEach(t => {{
                        if (t.getAttribute('onclick') && t.getAttribute('onclick').includes("'" + sourceSection + "'")) {{
                            t.classList.add('active');
                        }}
                    }});
                }}
            }}
        }}
        
        document.getElementById('modal').addEventListener('click', function(e) {{
            if (e.target === this) closeModal();
        }});
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeModal();
        }});
        
        // =====================================================================
        // SEARCH FUNCTIONALITY
        // =====================================================================
        
        // Search data will be populated from Python
        var searchData = {search_data_js};
        
        function escapeHtml(text) {{
            var div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        function highlightMatch(text, query) {{
            if (!query) return escapeHtml(text);
            var regex = new RegExp('(' + query.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
            return escapeHtml(text).replace(regex, '<span class="search-highlight">$1</span>');
        }}
        
        function searchViews(query) {{
            var results = [];
            var lowerQuery = query.toLowerCase();
            
            for (var viewId in searchData) {{
                var view = searchData[viewId];
                var score = 0;
                var matchReason = '';
                
                // Match on view ID
                if (viewId.toLowerCase().includes(lowerQuery)) {{
                    score += 100;
                    matchReason = 'ID match';
                }}
                
                // Match on display name
                if (view.displayName && view.displayName.toLowerCase().includes(lowerQuery)) {{
                    score += 80;
                    matchReason = matchReason || 'Name match';
                }}
                
                // Match on description
                if (view.description && view.description.toLowerCase().includes(lowerQuery)) {{
                    score += 30;
                    matchReason = matchReason || 'Description match';
                }}
                
                // Match on domain
                if (view.domain && view.domain.toLowerCase().includes(lowerQuery)) {{
                    score += 20;
                    matchReason = matchReason || 'Domain match';
                }}
                
                if (score > 0) {{
                    results.push({{
                        viewId: viewId,
                        displayName: view.displayName || viewId,
                        domain: view.domain,
                        domainDisplay: view.domainDisplay,
                        description: view.description,
                        score: score,
                        matchReason: matchReason,
                        type: 'view'
                    }});
                }}
            }}
            
            results.sort(function(a, b) {{ return b.score - a.score; }});
            return results.slice(0, 20);
        }}
        
        function searchProperties(query) {{
            var results = [];
            var lowerQuery = query.toLowerCase();
            
            for (var viewId in searchData) {{
                var view = searchData[viewId];
                if (!view.properties) continue;
                
                for (var i = 0; i < view.properties.length; i++) {{
                    var prop = view.properties[i];
                    var score = 0;
                    var matchReason = '';
                    
                    // Match on View Property (externalId)
                    if (prop.viewProperty && prop.viewProperty.toLowerCase().includes(lowerQuery)) {{
                        score += 100;
                        matchReason = 'View Property ID match';
                    }}
                    
                    // Match on View Property Name (display name)
                    if (prop.viewPropertyName && prop.viewPropertyName.toLowerCase().includes(lowerQuery)) {{
                        score += 90;
                        matchReason = matchReason || 'View Property Name match';
                    }}
                    
                    // Match on Container Property (externalId)
                    if (prop.containerProperty && prop.containerProperty.toLowerCase().includes(lowerQuery)) {{
                        score += 80;
                        matchReason = matchReason || 'Container Property ID match';
                    }}
                    
                    // Match on Container Property Name (display name)
                    if (prop.containerPropertyName && prop.containerPropertyName.toLowerCase().includes(lowerQuery)) {{
                        score += 70;
                        matchReason = matchReason || 'Container Property Name match';
                    }}
                    
                    // Match on property type (target externalId)
                    if (prop.type && prop.type.toLowerCase().includes(lowerQuery)) {{
                        score += 50;
                        matchReason = matchReason || 'Target type match';
                    }}
                    
                    // Match on property type display name
                    if (prop.typeDisplay && prop.typeDisplay.toLowerCase().includes(lowerQuery)) {{
                        score += 40;
                        matchReason = matchReason || 'Target name match';
                    }}
                    
                    if (score > 0) {{
                        results.push({{
                            viewId: viewId,
                            viewDisplayName: view.displayName || viewId,
                            viewProperty: prop.viewProperty,
                            viewPropertyName: prop.viewPropertyName,
                            containerProperty: prop.containerProperty,
                            containerPropertyName: prop.containerPropertyName,
                            propertyType: prop.type,
                            propertyTypeDisplay: prop.typeDisplay,
                            isRelation: prop.isRelation,
                            inherited: prop.inherited,
                            score: score,
                            matchReason: matchReason,
                            type: 'property'
                        }});
                    }}
                }}
            }}
            
            results.sort(function(a, b) {{ return b.score - a.score; }});
            return results.slice(0, 30);
        }}
        
        // Dual search state
        var viewSearchInput = document.getElementById('viewSearchInput');
        var propSearchInput = document.getElementById('propSearchInput');
        var viewSearchResults = document.getElementById('viewSearchResults');
        var propSearchResults = document.getElementById('propSearchResults');
        var viewFilter = document.getElementById('viewFilter');
        var propFilter = document.getElementById('propFilter');
        var viewSearchTimeout, propSearchTimeout;
        var selectedViewFilter = null; // Filter properties by this view
        var selectedPropFilter = null; // Filter views by this property
        
        function renderViewResults(results, query) {{
            if (results.length === 0) {{
                viewSearchResults.innerHTML = '<div class="search-count">No results found</div>';
                viewSearchResults.classList.add('active');
                return;
            }}
            
            var html = '<div class="search-count">' + results.length + ' view(s) <span style="opacity:0.5;font-size:0.8em">(Shift+click to filter properties)</span></div>';
            
            for (var i = 0; i < results.length; i++) {{
                var r = results[i];
                html += '<div class="search-result-item" onclick="handleViewClick(event, \\'' + r.viewId + '\\')">';
                html += '<div class="search-result-title">' + highlightMatch(r.displayName, query);
                if (r.viewId !== r.displayName) {{
                    html += ' <span style="opacity:0.6;font-size:0.8em">(' + highlightMatch(r.viewId, query) + ')</span>';
                }}
                html += '</div>';
                html += '<div class="search-result-meta">';
                if (r.description) {{
                    html += highlightMatch(r.description.substring(0, 80), query);
                    if (r.description.length > 80) html += '...';
                }}
                html += '</div></div>';
            }}
            
            viewSearchResults.innerHTML = html;
            viewSearchResults.classList.add('active');
        }}
        
        function handleViewClick(e, viewId) {{
            if (e.shiftKey) {{
                setViewFilter(viewId);
            }} else {{
                goToView(viewId);
            }}
        }}
        
        function renderPropResults(results, query) {{
            if (results.length === 0) {{
                propSearchResults.innerHTML = '<div class="search-count">No results found</div>';
                propSearchResults.classList.add('active');
                return;
            }}
            
            var html = '<div class="search-count">' + results.length + ' propert' + (results.length === 1 ? 'y' : 'ies') + '</div>';
            
            for (var i = 0; i < results.length; i++) {{
                var r = results[i];
                html += '<div class="search-result-item" onclick="goToView(\\'' + r.viewId + '\\')">';
                html += '<div class="search-result-title">';
                if (r.viewPropertyName && r.viewPropertyName !== r.viewProperty) {{
                    html += highlightMatch(r.viewPropertyName, query);
                    html += ' <span class="search-result-property">(' + highlightMatch(r.viewProperty, query) + ')</span>';
                }} else {{
                    html += '<span class="search-result-property">' + highlightMatch(r.viewProperty || '', query) + '</span>';
                }}
                if (r.isRelation) html += ' <span style="color:var(--accent-emerald)">→</span>';
                html += '</div>';
                if (r.containerProperty) {{
                    html += '<div class="search-result-container">';
                    html += '<span style="opacity:0.6">Container: </span>';
                    if (r.containerPropertyName && r.containerPropertyName !== r.containerProperty) {{
                        html += highlightMatch(r.containerPropertyName, query) + ' <span style="opacity:0.6">(' + highlightMatch(r.containerProperty, query) + ')</span>';
                    }} else {{
                        html += highlightMatch(r.containerProperty, query);
                    }}
                    html += '</div>';
                }}
                html += '<div class="search-result-meta">in <strong>' + escapeHtml(r.viewDisplayName) + '</strong>';
                if (r.propertyType) {{
                    if (r.propertyTypeDisplay && r.propertyTypeDisplay !== r.propertyType) {{
                        html += ' &bull; → ' + r.propertyTypeDisplay;
                    }} else {{
                        html += ' &bull; ' + r.propertyType;
                    }}
                }}
                html += '</div></div>';
            }}
            
            propSearchResults.innerHTML = html;
            propSearchResults.classList.add('active');
        }}
        
        function setViewFilter(viewId) {{
            selectedViewFilter = viewId;
            var viewData = searchData[viewId];
            var name = viewData ? viewData.displayName : viewId;
            viewFilter.innerHTML = 'Filtering properties by: <strong>' + name + '</strong><span class="clear-filter" onclick="clearViewFilter(event)">[clear]</span>';
            // Re-run property search with filter
            performPropSearch();
        }}
        
        function clearViewFilter(e) {{
            e.stopPropagation();
            selectedViewFilter = null;
            viewFilter.innerHTML = '';
            performPropSearch();
        }}
        
        function goToView(viewId) {{
            viewSearchResults.classList.remove('active');
            propSearchResults.classList.remove('active');
            viewSearchInput.value = '';
            propSearchInput.value = '';
            viewFilter.innerHTML = '';
            propFilter.innerHTML = '';
            selectedViewFilter = null;
            
            var card = document.querySelector('.card[data-view-id="' + viewId + '"]') ||
                       document.querySelector('.card[data-node-id="' + viewId + '"]');
            if (card) {{
                var section = card.closest('.section');
                if (section) {{
                    var sectionId = section.id;
                    document.querySelectorAll('.section').forEach(function(s) {{ s.classList.remove('active'); }});
                    document.querySelectorAll('.nav-tab').forEach(function(t) {{ t.classList.remove('active'); }});
                    section.classList.add('active');
                    document.querySelectorAll('.nav-tab').forEach(function(t) {{
                        if (t.getAttribute('onclick') && t.getAttribute('onclick').includes("'" + sectionId + "'")) {{
                            t.classList.add('active');
                        }}
                    }});
                }}
                setTimeout(function() {{
                    card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    card.style.boxShadow = '0 0 20px var(--accent-gold)';
                    setTimeout(function() {{ card.style.boxShadow = ''; }}, 2000);
                }}, 100);
            }}
        }}
        
        function performViewSearch() {{
            var query = viewSearchInput.value.trim();
            
            // Check for wildcard with property filter active
            var propQuery = propSearchInput.value.trim();
            var isWildcard = (query === '*');
            
            if (!isWildcard && query.length < 2) {{
                viewSearchResults.classList.remove('active');
                viewFilter.innerHTML = '';
                return;
            }}
            
            // Wildcard: show all views filtered by property search
            if (isWildcard && propQuery.length >= 2) {{
                var propResults = searchProperties(propQuery);
                var viewsWithMatchingProps = {{}};
                propResults.forEach(function(p) {{ viewsWithMatchingProps[p.viewId] = true; }});
                var results = [];
                Object.keys(searchData).forEach(function(viewId) {{
                    if (viewsWithMatchingProps[viewId]) {{
                        results.push({{
                            viewId: viewId,
                            displayName: searchData[viewId].displayName,
                            description: searchData[viewId].description,
                            score: 100
                        }});
                    }}
                }});
                results.sort(function(a, b) {{ return a.displayName.localeCompare(b.displayName); }});
                viewFilter.innerHTML = '<span style="color:var(--accent-emerald)">All views with property: "' + escapeHtml(propQuery) + '"</span>';
                renderViewResults(results, '');
                return;
            }} else if (isWildcard) {{
                viewSearchResults.classList.remove('active');
                viewFilter.innerHTML = '<span style="color:var(--text-muted)">Enter property search first to use wildcard</span>';
                return;
            }}
            
            var results = searchViews(query);
            
            // Cross-filter: if property search has text, filter to views containing matching properties
            if (propQuery.length >= 2) {{
                var propResults = searchProperties(propQuery);
                var viewsWithMatchingProps = {{}};
                propResults.forEach(function(p) {{ viewsWithMatchingProps[p.viewId] = true; }});
                results = results.filter(function(r) {{ return viewsWithMatchingProps[r.viewId]; }});
                viewFilter.innerHTML = '<span style="color:var(--accent-emerald)">Filtered by property: "' + escapeHtml(propQuery) + '"</span>';
            }} else {{
                viewFilter.innerHTML = '';
            }}
            
            renderViewResults(results, query);
        }}
        
        function performPropSearch() {{
            var query = propSearchInput.value.trim();
            
            // Check for wildcard with view filter active
            var viewQuery = viewSearchInput.value.trim();
            var isWildcard = (query === '*');
            
            if (!isWildcard && query.length < 2) {{
                propSearchResults.classList.remove('active');
                propFilter.innerHTML = '';
                return;
            }}
            
            // Wildcard: show all properties filtered by view search
            if (isWildcard && viewQuery.length >= 2) {{
                var viewResults = searchViews(viewQuery);
                var matchingViews = {{}};
                viewResults.forEach(function(v) {{ matchingViews[v.viewId] = true; }});
                var results = [];
                Object.keys(searchData).forEach(function(viewId) {{
                    if (matchingViews[viewId]) {{
                        var props = searchData[viewId].properties || [];
                        props.forEach(function(prop) {{
                            results.push({{
                                viewId: viewId,
                                viewDisplayName: searchData[viewId].displayName,
                                viewProperty: prop.name,
                                viewPropertyName: prop.displayName,
                                containerProperty: prop.containerProperty,
                                containerPropertyName: prop.containerPropertyName,
                                propertyType: prop.type,
                                propertyTypeDisplay: prop.typeDisplay,
                                isRelation: prop.isRelation,
                                inherited: prop.inherited,
                                score: 100
                            }});
                        }});
                    }}
                }});
                results.sort(function(a, b) {{ 
                    var nameA = a.viewPropertyName || a.viewProperty || '';
                    var nameB = b.viewPropertyName || b.viewProperty || '';
                    return nameA.localeCompare(nameB); 
                }});
                propFilter.innerHTML = '<span style="color:var(--accent-emerald)">All properties from view: "' + escapeHtml(viewQuery) + '"</span>';
                renderPropResults(results, '');
                return;
            }} else if (isWildcard) {{
                propSearchResults.classList.remove('active');
                propFilter.innerHTML = '<span style="color:var(--text-muted)">Enter view search first to use wildcard</span>';
                return;
            }}
            
            var results = searchProperties(query);
            
            // Cross-filter: if view search has text, filter to properties from matching views
            if (viewQuery.length >= 2) {{
                var viewResults = searchViews(viewQuery);
                var matchingViews = {{}};
                viewResults.forEach(function(v) {{ matchingViews[v.viewId] = true; }});
                results = results.filter(function(r) {{ return matchingViews[r.viewId]; }});
                propFilter.innerHTML = '<span style="color:var(--accent-emerald)">Filtered by view: "' + escapeHtml(viewQuery) + '"</span>';
            }} else if (selectedViewFilter) {{
                // Manual filter via shift+click
                results = results.filter(function(r) {{ return r.viewId === selectedViewFilter; }});
            }} else {{
                propFilter.innerHTML = '';
            }}
            
            renderPropResults(results, query);
        }}
        
        viewSearchInput.addEventListener('input', function() {{
            clearTimeout(viewSearchTimeout);
            viewSearchTimeout = setTimeout(function() {{
                performViewSearch();
                // If property field has wildcard, update its results too
                if (propSearchInput.value.trim() === '*') {{
                    performPropSearch();
                }}
            }}, 200);
        }});
        
        propSearchInput.addEventListener('input', function() {{
            clearTimeout(propSearchTimeout);
            propSearchTimeout = setTimeout(function() {{
                performPropSearch();
                // If view field has wildcard, update its results too
                if (viewSearchInput.value.trim() === '*') {{
                    performViewSearch();
                }}
            }}, 200);
        }});
        
        viewSearchInput.addEventListener('focus', function() {{
            // Always re-run search on focus to apply cross-filter from other field
            if (viewSearchInput.value.trim().length >= 2) {{
                performViewSearch();
            }} else if (propSearchInput.value.trim().length >= 2) {{
                // Show hint that filtering will apply when typing
                viewFilter.innerHTML = '<span style="color:var(--text-muted)">Results will be filtered by property: "' + escapeHtml(propSearchInput.value.trim()) + '"</span>';
            }}
        }});
        
        propSearchInput.addEventListener('focus', function() {{
            // Always re-run search on focus to apply cross-filter from other field
            if (propSearchInput.value.trim().length >= 2) {{
                performPropSearch();
            }} else if (viewSearchInput.value.trim().length >= 2) {{
                // Show hint that filtering will apply when typing
                propFilter.innerHTML = '<span style="color:var(--text-muted)">Results will be filtered by view: "' + escapeHtml(viewSearchInput.value.trim()) + '"</span>';
            }}
        }});
        
        // Close search results when clicking outside
        document.addEventListener('click', function(e) {{
            if (!e.target.closest('.search-box')) {{
                viewSearchResults.classList.remove('active');
                propSearchResults.classList.remove('active');
            }}
        }});
        
        // Keyboard navigation
        viewSearchInput.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                viewSearchResults.classList.remove('active');
                viewSearchInput.blur();
            }}
        }});
        propSearchInput.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                propSearchResults.classList.remove('active');
                propSearchInput.blur();
            }}
        }});
        
        // =====================================================================
        // THEME TOGGLE
        // =====================================================================
        
        var themeToggle = document.getElementById('themeToggle');
        var htmlElement = document.documentElement;
        
        // Load saved theme or default to dark
        var savedTheme = localStorage.getItem('neatDocTheme');
        if (savedTheme === 'light') {{
            htmlElement.setAttribute('data-theme', 'light');
            themeToggle.checked = true;
        }}
        
        themeToggle.addEventListener('change', function() {{
            if (this.checked) {{
                htmlElement.setAttribute('data-theme', 'light');
                localStorage.setItem('neatDocTheme', 'light');
            }} else {{
                htmlElement.removeAttribute('data-theme');
                localStorage.setItem('neatDocTheme', 'dark');
            }}
        }});
    </script>
</body>
</html>'''
    
    return html


# =============================================================================
# PROGRAMMATIC ENTRY POINT  (used by html-doc-plugin and other callers)
# =============================================================================

def run_generation(input_path, output_path, cdm_path=None, idm_path=None):
    """Generate HTML documentation from a NEAT YAML or Excel data model file.

    This is the public, importable entry point for programmatic use.
    The CLI ``main()`` wraps this function.

    Args:
        input_path: Path to .yaml, .yml, or .xlsx NEAT data model file.
        output_path: Destination path for the generated .html file.
        cdm_path: Optional path to the Cognite Core Data Model YAML
                  (auto-discovered alongside the input file if omitted).
        idm_path: Optional path to a Cognite Process Industries YAML
                  (cdf_idm space, auto-discovered or bundled fallback).
    """
    input_path  = Path(input_path)
    output_path = Path(output_path)
    base_dir    = input_path.parent

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # ── CDM auto-discovery ───────────────────────────────────────────────────
    if cdm_path is None:
        for p in [base_dir / 'SierraCol' / 'CogniteCore.yaml',
                  base_dir / 'CogniteCore.yaml',
                  Path(__file__).parent / 'CogniteCore.yaml']:
            if p.exists():
                cdm_path = p
                break

    # ── IDM auto-discovery ───────────────────────────────────────────────────
    if idm_path is None:
        for p in [base_dir / 'CogniteProcessIndustries.yaml',
                  Path(__file__).parent / 'CogniteProcessIndustries.yaml']:
            if p.exists():
                idm_path = p
                break

    print(f"\n{'='*70}")
    print(f"NEAT Documentation Generator v6 - Domain Model Centric")
    print(f"{'='*70}")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")

    suffix = input_path.suffix.lower()
    print(f"\nParsing {input_path.name}...")
    if suffix in ('.xlsx', '.xls'):
        metadata, properties_by_view, all_views, direct_relations = parse_excel_file(str(input_path))
    else:
        metadata, properties_by_view, all_views, direct_relations = parse_yaml_file(str(input_path))

    model_name  = metadata.get('name', input_path.stem.replace('_', ' ').title())
    space       = metadata.get('space', input_path.stem)
    external_id = metadata.get('externalId', input_path.stem)
    version     = metadata.get('version', '')
    description = metadata.get('description', f'Data model from {input_path.name}')

    domain_view_ids = {k for k in all_views.keys() if not k.startswith('Cognite')}

    print(f"  Model: {model_name}")
    print(f"  Domain views: {len(all_views)}")
    print(f"  Relations: {len(direct_relations)}")

    if cdm_path and Path(cdm_path).exists():
        print(f"\nLoading CDM from {Path(cdm_path).name}...")
        cdm_meta, cdm_props, cdm_views, _ = parse_yaml_file(str(cdm_path))
        cdm_version = cdm_meta.get('version', '')
        cdm_space   = cdm_meta.get('space', 'cdf_cdm')
        print(f"  CDM views: {len(cdm_views)}")
        for k, v in cdm_views.items():
            if k not in all_views:
                all_views[k] = dict(v, _model_version=cdm_version, _model_space=cdm_space)
        for k, v in cdm_props.items():
            if k not in properties_by_view:
                properties_by_view[k] = v

    if idm_path and Path(idm_path).exists():
        print(f"\nLoading IDM from {Path(idm_path).name}...")
        idm_meta, idm_props, idm_views, _ = parse_yaml_file(str(idm_path))
        idm_version = idm_meta.get('version', '')
        idm_space   = idm_meta.get('space', 'cdf_idm')
        idm_added = 0
        for k, v in idm_views.items():
            # Plain name (e.g. CogniteOperation) — for CDM-parent lookups.
            # Mark views that are NEW here (not already in CDM or domain) as IDM-specific
            # so the hierarchy can distinguish them from true CDM types.
            if k not in all_views:
                all_views[k] = dict(v, _idm_specific=True,
                                    _model_version=idm_version, _model_space=idm_space)
                idm_added += 1
            # Namespace-prefixed (e.g. cdf_idm:CogniteOperation) — canonical IDM form
            nk = f'cdf_idm:{k}'
            if nk not in all_views:
                all_views[nk] = dict(v, _idm_specific=True,
                                     _model_version=idm_version, _model_space=idm_space)
        for k, v in idm_props.items():
            if k not in properties_by_view:
                properties_by_view[k] = v
            nk = f'cdf_idm:{k}'
            if nk not in properties_by_view:
                properties_by_view[nk] = v
        print(f"  IDM views: {idm_added} new")

    inheritance_depths = {}
    for v in all_views:
        inheritance_depths[v] = get_inheritance_depth(v, all_views, inheritance_depths)

    is_cdm = 'CogniteCore' in input_path.name

    core_cdm_types = {
        'CogniteDescribable', 'CogniteSourceable', 'CogniteVisualizable',
        'CogniteSchedulable', 'CogniteAsset', 'CogniteEquipment',
        'CogniteTimeSeries', 'CogniteActivity', 'CogniteFile',
        'CogniteAssetClass', 'CogniteEquipmentType', 'CogniteUnit',
        'CogniteSourceSystem', 'Cognite3DObject', 'CognitePointCloudVolume'
    }

    views = {}
    print(f"\n  Processing {len(all_views)} views")
    for view_id, view_info in all_views.items():
        if not is_cdm and view_id.startswith('Cognite'):
            if view_id not in core_cdm_types:
                continue
        elif not is_cdm and view_id not in domain_view_ids:
            # Non-Cognite views added purely for context (e.g. cdf_idm: namespaced
            # copies from the IDM YAML) — skip so they don't appear as entity cards.
            continue
        props = get_all_properties_for_view(view_id, properties_by_view, all_views)
        own   = sum(1 for p in props if not p.get('inherited_from'))
        views[view_id] = {
            'name':                     view_info.get('name', view_id),
            'display_name':             view_info.get('display_name', ''),
            'description':              view_info.get('description', ''),
            'implements':               view_info.get('implements', ''),
            'properties':               props,
            'own_property_count':       own,
            'inherited_property_count': len(props) - own,
        }

    print("\nCategorizing by industry domain...")
    categories, category_labels, view_domains = categorize_by_industry_domain(views, all_views)
    for cat, vlist in sorted(categories.items()):
        if vlist:
            domain_info = DOMAIN_CATEGORIES.get(cat, {})
            icon = domain_info.get('icon', '📦')
            name = domain_info.get('display_name', cat)
            print(f"  {icon} {name}: {len(vlist)}")

    icons = generate_icons(views)

    print("\nGenerating UML diagrams...")
    html = generate_html(model_name, space, description, views, all_views, inheritance_depths,
                         categories, category_labels, icons, direct_relations, view_domains,
                         domain_view_ids=domain_view_ids,
                         external_id=external_id, version=version)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n{'='*70}")
    print(f"Generated: {output_path}")
    print(f"{'='*70}\n")
    return output_path


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate UML-style HTML documentation from a NEAT data model '
                    '(accepts both .yaml/.yml and .xlsx input files)'
    )
    parser.add_argument(
        'input_file',
        help='Path to the NEAT data model file (.yaml, .yml, or .xlsx)'
    )
    parser.add_argument('--cdm', help='Path to Cognite Core Data Model YAML (CogniteCore.yaml)')
    parser.add_argument('--idm', help='Path to Cognite Industrial Data Model YAML (CogniteProcessIndustries.yaml)')
    parser.add_argument('-o', '--output', help='Output HTML file path (defaults to <input>.html)')

    args = parser.parse_args()

    base_dir   = Path(__file__).parent
    input_path = Path(args.input_file)
    if not input_path.is_absolute():
        input_path = base_dir / input_path

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    cdm_path = None
    if args.cdm:
        cdm_path = Path(args.cdm)
        if not cdm_path.is_absolute():
            cdm_path = base_dir / cdm_path

    idm_path = None
    if args.idm:
        idm_path = Path(args.idm)
        if not idm_path.is_absolute():
            idm_path = base_dir / idm_path

    output_path = Path(args.output) if args.output else input_path.with_suffix('.html')
    if not output_path.is_absolute():
        output_path = base_dir / output_path

    run_generation(input_path, output_path, cdm_path, idm_path)


if __name__ == '__main__':
    main()
