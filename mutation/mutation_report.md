# Mutation report

Written by `python mutation/mutate.py`. Each mutant is one deliberate bug planted in a copy of the repository; it is *killed* when the listed tests fail. Controls: the unmodified copy passed, and a harmless comment edit survived.

**42 of 42 mutants killed.**

No survivors.

| Mutant | File | Planted bug | Tests run | Result | First failing test |
|---|---|---|---|---|---|
| Gst_rate_8pct | `src/boa/valuation.py` | Singapore GST at the 2023 rate | test_valuation.py | killed | tests/test_valuation.py::test_singapore_gst |
| Gst_ignores_duty | `src/boa/valuation.py` | GST base leaves out the duty | test_valuation.py | killed | tests/test_valuation.py::test_singapore_gst |
| Cif_fob_drops_insurance | `src/boa/valuation.py` | FOB invoice: insurance not added to the CIF value | test_valuation.py | killed | tests/test_valuation.py::test_fob_with_actual_charges |
| Cif_flat_rate_for_fca | `src/boa/valuation.py` | flat freight-and-insurance rate applied to FCA quotes (published for FOB only) | test_valuation.py | killed | tests/test_valuation.py::test_fca_and_fas_have_no_flat_rate |
| Cif_cfr_flat_insurance_2pct | `src/boa/valuation.py` | flat CFR insurance doubled | test_valuation.py | killed | tests/test_valuation.py::test_cfr_insurance_flat_one_percent |
| Fob_keeps_insurance_in_cif_price | `src/boa/valuation.py` | FOB value from a CIF price leaves the insurance in | test_valuation.py | killed | tests/test_valuation.py::test_fob_value_for_exports_and_australia |
| Au_voti_drops_transport | `src/boa/valuation.py` | Australian GST base without transport and insurance | test_valuation.py | killed | tests/test_valuation.py::test_australian_gst_on_voti |
| Au_n10_threshold_inclusive | `src/boa/valuation.py` | Import Declaration required at exactly AUD 1,000 (rule: over 1,000) | test_valuation.py | killed | tests/test_valuation.py::test_australian_declaration_type[1000.0-False-False-Self-Assessed Clearance] |
| Hs_checks_chapter_only | `src/boa/hs.py` | HS validity tested at chapter level, so deleted subheadings pass | test_hs_uen.py | killed | tests/test_hs_uen.py::test_sg_hs_check[85171200-hs6_unknown] |
| Hs_accepts_7_digits | `src/boa/hs.py` | 7-digit HS codes accepted for Singapore | test_hs_uen.py | killed | tests/test_hs_uen.py::test_sg_hs_check[8517130-format] |
| Uen_lowercase_check_letter | `src/boa/uen.py` | UEN with a lower-case check letter accepted | test_hs_uen.py | killed | tests/test_hs_uen.py::test_uen_formats[200912345k-None] |
| Score_blocking_weight | `src/boa/validator.py` | readiness score weight changed | test_validator.py | killed | tests/test_validator.py::test_missing_incoterm_blocks_and_skips_value_check |
| Band_warning_reads_ready | `src/boa/validator.py` | a shipment with warnings is reported Ready | test_validator.py | killed | tests/test_validator.py::test_readiness_score_arithmetic |
| Permit_timing_reversed | `src/boa/validator.py` | permit-before-arrival check reversed | test_validator.py | killed | tests/test_validator.py::test_clean_bundle_is_ready_with_gst_estimate |
| Value_tolerance_5pct | `src/boa/validator.py` | declared value may differ by 5% instead of 0.5% | test_validator.py | killed | tests/test_validator.py::test_value_within_tolerance_passes |
| Weight_tolerance_5pct | `src/boa/validator.py` | gross weights may differ by 5% instead of 2% | test_validator.py | killed | tests/test_validator.py::test_quantities_weights_and_documents |
| Licence_date_ignored | `src/boa/validator.py` | a licence obtained after the permit counts as on file | test_validator.py | killed | tests/test_validator.py::test_controlled_goods_need_licence_on_file_and_quoted |
| Licence_any_reference_accepted | `src/boa/validator.py` | any quoted reference satisfies every authority of a line | test_validator.py | killed | tests/test_validator.py::test_controlled_goods_need_licence_on_file_and_quoted |
| Origin_check_inverted | `src/boa/validator.py` | origin mismatch check inverted | test_validator.py | killed | tests/test_validator.py::test_clean_bundle_is_ready_with_gst_estimate |
| Preference_needs_no_proof | `src/boa/validator.py` | preference without proof of origin passes | test_validator.py | killed | tests/test_validator.py::test_origin_checks |
| Sg_controls_applied_to_exports | `src/boa/validator.py` | Singapore import controls applied to exports | test_validator.py | killed | tests/test_validator.py::test_export_to_australia |
| Cancel_window_7_days | `src/boa/validator.py` | expired permits treated as cancellable for a week (rule: 1 calendar day) | test_validator.py | killed | tests/test_validator.py::test_corrective_action_route |
| Pareto_ascending | `src/boa/analytics.py` | Pareto sorted from the rarest reason | test_analytics.py | killed | tests/test_analytics.py::test_pareto_hand_worked |
| Percentile_lower | `src/boa/analytics.py` | percentiles without interpolation (differs from DAX) | test_analytics.py | killed | tests/test_analytics.py::test_percentiles_are_linear_like_dax |
| Vital_few_strict | `src/boa/analytics.py` | vital-few cut-off excludes a reason that lands exactly on the threshold | test_analytics.py | killed | tests/test_analytics.py::test_pareto_hand_worked |
| Detection_ignores_warnings | `src/boa/analytics.py` | holds flagged only by a warning counted as not detected | test_analytics.py | killed | tests/test_analytics.py::test_detection_and_blocking_precision |
| Kpi_hold_rate_inverted | `src/boa/kpis.py` | hold rate numerator and denominator swapped | test_kpis.py | killed | tests/test_kpis.py::test_pandas_matches_hand_value[First-3 Hold Rate %-19] |
| Kpi_pareto_tie_break | `src/boa/kpis.py` | Pareto cumulative share leaves out the reason itself when counts tie | test_kpis.py | killed | tests/test_kpis.py::test_pandas_matches_hand_value[Hold Pareto Cumulative %-36] |
| Kpi_step_conversion_vs_first_stage | `src/boa/kpis.py` | step conversion divides by the first stage instead of the previous one | test_kpis.py | killed | tests/test_kpis.py::test_pandas_matches_hand_value[Step Conversion %-10] |
| Clf_heldout_templates_leak | `src/boa/classifier.py` | held-out-template notes leak into the training pool | test_classifier.py | killed | tests/test_classifier.py::test_split_is_disjoint_and_template_held_out |
| Clf_accuracy_is_error_rate | `src/boa/classifier.py` | accuracy computed as the error rate | test_classifier.py | killed | tests/test_classifier.py::test_metrics_hand_worked |
| Dax_hold_rate_per_customer | `powerbi/BrokerageOnboard.SemanticModel/definition/tables/FactShipment.tmdl` | hold rate divided by customers instead of shipments | test_kpis.py, test_measures.py | killed | tests/test_kpis.py::test_dax_matches_hand_value[First-3 Hold Rate %-19] |
| Dax_median_is_average | `powerbi/BrokerageOnboard.SemanticModel/definition/tables/FactShipment.tmdl` | median clearance hours computed as the mean | test_kpis.py, test_measures.py | killed | tests/test_kpis.py::test_dax_matches_hand_value[Median Clearance Hours-29] |
| Dax_open_actions_overrides_slicer | `powerbi/BrokerageOnboard.SemanticModel/definition/tables/FactAction.tmdl` | Open Actions ignores a Status slicer (KEEPFILTERS removed) | test_kpis.py, test_measures.py | killed | tests/test_kpis.py::test_dax_matches_hand_value[Open Actions-52] |
| Dax_pareto_ties_double_counted | `powerbi/BrokerageOnboard.SemanticModel/definition/tables/FactHold.tmdl` | Pareto cumulative share counts every tied reason | test_kpis.py, test_measures.py | killed | tests/test_kpis.py::test_dax_matches_hand_value[Hold Pareto Cumulative %-40] |
| Dax_stage_conversion_keeps_stage_filter | `powerbi/BrokerageOnboard.SemanticModel/definition/tables/FactEnrolmentStage.tmdl` | Enrolments Submitted keeps the selected stage's filter, so conversion is blank or 100% | test_kpis.py, test_measures.py | killed | tests/test_kpis.py::test_dax_matches_hand_value[Enrolments Submitted-3] |
| Relationship_hold_lane_on_name | `powerbi/BrokerageOnboard.SemanticModel/definition/relationships.tmdl` | holds joined to lanes on the wrong column | test_measures.py | killed | tests/test_measures.py::test_measure_matches_pandas[Holds-12] |
| Engine_keepfilters_replaces | `pbitest/dax.py` | evaluator treats KEEPFILTERS like a plain filter | test_dax_engine.py | killed | tests/test_dax_engine.py::test_keepfilters_intersects_instead_of_replacing |
| Engine_no_context_transition | `pbitest/dax.py` | measure references inside an iterator ignore the current row | test_dax_engine.py | killed | tests/test_dax_engine.py::test_filter_sumx_and_context_transition |
| Synth_held_flag_always_false | `src/boa/synth.py` | shipments never marked held although hold rows exist | test_synth.py | killed | tests/test_synth.py::test_holds_agree_with_shipments |
| Synth_due_date_one_day_late | `src/boa/synth.py` | action due dates one day after the documented SLA | test_synth.py | killed | tests/test_synth.py::test_actions_are_consistent |
| Rule_table_china_flat_rate | `rules/sg_flat_freight_insurance.csv` | published flat rate for China mistyped | test_rules.py, test_valuation.py | killed | tests/test_rules.py::test_flat_rates_table |
