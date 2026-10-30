"""Staged prototype-readiness assessment, separate from production qualification.

Native results and review facts must be established by the calling audit; this
pure function neither authenticates human reviews nor releases files, orders a
board, or permits hardware power. Unknown facts block only their own stage and
its dependants. Post-prototype EVT is not a prerequisite for the first bare PCB.
"""

STAGES = {
    'bare_pcb_sample': {
        'depends_on': (),
        'requires': (
            'source_bindings_and_libraries_verified',
            'original_native_pad_groups_preserved',
            'all_native_ground_pads_connected',
            'schematic_and_power_design_review',
            'board_envelope_and_connector_review',
            'stackup_finish_and_filled_via_process_review',
            'gerber_drill_and_cam_review',
        ),
    },
    'assembled_board_sample': {
        'depends_on': ('bare_pcb_sample',),
        'requires': ('bom_exact_mpn_footprint_review', 'cpl_rotation_side_review',
                     'stencil_and_assembly_process_review'),
    },
    'specified_device_prototype': {
        'depends_on': ('assembled_board_sample',),
        'requires': ('exact_battery_identity_and_interface',
                     'exact_panel_touch_frontlight_assembly',
                     'finished_positive_tolerance_stack_review'),
    },
    'first_current_limited_board_power': {
        'depends_on': ('assembled_board_sample',),
        'requires': ('as_built_visual_and_short_check',
                     'current_limited_power_sequence_review'),
    },
    'first_battery_charge': {
        'depends_on': ('first_current_limited_board_power',),
        'requires': ('exact_battery_identity_and_interface',
                     'charger_pack_protection_ntc_compatibility',
                     'controlled_charge_test_plan_review'),
    },
    'production_qualification': {
        'depends_on': ('specified_device_prototype', 'first_battery_charge'),
        'requires': ('physical_evt_complete', 'rf_emi_thermal_validation',
                     'reliability_and_manufacturing_qualification'),
    },
}
REVIEW_FACTS = frozenset(fact for stage in STAGES.values() for fact in stage['requires'])
NATIVE_COUNTERS = ('drc_errors', 'drc_warnings', 'open', 'parity', 'erc')


def assess_prototype_stages(native_counts, review_facts):
    """Return fail-closed stage blockers from verified observations/review decisions.

    Facts are tri-state: True=verified, False=known unmet, None=not established.
    Counts must be actual nonnegative integers, not truthy strings or booleans.
    Native `open` counts are independent of DRC rule-error counts.
    """
    if (not isinstance(native_counts, dict)
            or set(native_counts) not in ({'Single'}, {'Core', 'Display'})):
        raise ValueError('Exact Single or historical Core/Display reports are required')
    if not isinstance(review_facts, dict) or set(review_facts) - REVIEW_FACTS:
        raise ValueError('Unknown or malformed prototype review facts')
    if any(value is not None and type(value) is not bool for value in review_facts.values()):
        raise ValueError('Prototype review facts must be true, false or unknown')
    native_blockers = []
    for board, report in native_counts.items():
        if not isinstance(report, dict):
            raise ValueError('Invalid native board report')
        for name in NATIVE_COUNTERS:
            value = report.get(name)
            if type(value) is not int or value < 0:
                raise ValueError('Missing or invalid native counter: ' + board + '.' + name)
            if value:
                native_blockers.append({'id': board + '.' + name, 'observed': value,
                                        'required': 0, 'state': 'known_unmet'})
    stages = {}
    for name, definition in STAGES.items():
        blockers = list(native_blockers) if name == 'bare_pcb_sample' else []
        blockers.extend({'id': 'stage:' + dependency, 'state': 'prerequisite_not_ready'}
                        for dependency in definition['depends_on']
                        if not stages[dependency]['requirements_met'])
        for fact in definition['requires']:
            value = review_facts.get(fact)
            if value is not True:
                blockers.append({'id': fact, 'state': 'known_unmet' if value is False else 'not_established'})
        stages[name] = {'requirements_met': not blockers, 'blockers': blockers}
    return {
        'schema': 'panda47-staged-prototype-readiness-v1',
        'scope': 'assessment_only_not_fabrication_or_power_authorization',
        'stages': stages,
        'post_prototype_tests_are_not_bare_pcb_prerequisites': True,
        'orders_submitted': False,
    }
