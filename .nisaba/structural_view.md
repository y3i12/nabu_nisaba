**search query**: "EditorManager editor_manager"

- nabu_nisaba <!-- nabu_nisaba -->
    ├─- cpp_root <!-- nabu_nisaba.cpp_root -->
    │   ├─+ core [7+] <!-- nabu_nisaba.cpp_root::core -->
    │   └─- utils <!-- nabu_nisaba.cpp_root::utils -->
    │       ├─+ Helper [2+] <!-- nabu_nisaba.cpp_root::utils.Helper -->
    │       ├─+ Logger [3+] <!-- nabu_nisaba.cpp_root::utils.Logger -->
    │       ├─· Logger <!-- nabu_nisaba.cpp_root::utils.Logger.Logger -->
    │       ├─· disable ● 0.02 <!-- nabu_nisaba.cpp_root::utils.Logger.disable -->
    │       ├─· formatOutput <!-- nabu_nisaba.cpp_root::utils.Helper.formatOutput -->
    │       ├─· log <!-- nabu_nisaba.cpp_root::utils.Logger.log -->
    │       └─· validateInput <!-- nabu_nisaba.cpp_root::utils.Helper.validateInput -->
    ├─+ java_root [1+] <!-- nabu_nisaba.java_root -->
    ├─+ perl_root [2+] <!-- nabu_nisaba.perl_root -->
    └─- python_root <!-- nabu_nisaba.python_root -->
        ├─+ core [2+] <!-- nabu_nisaba.python_root.core -->
        ├─- nabu <!-- nabu_nisaba.python_root.nabu -->
        │   ├─+ core [36+] <!-- nabu_nisaba.python_root.nabu.core -->
        │   ├─- db <!-- nabu_nisaba.python_root.nabu.db -->
        │   │   └─- KuzuConnectionManager <!-- nabu_nisaba.python_root.nabu.db.KuzuConnectionManager -->
        │   │       ├─· __init__ ● 0.01 <!-- nabu_nisaba.python_root.nabu.db.KuzuConnectionManager.__init__ -->
        │   │       ├─· close ● 0.01 <!-- nabu_nisaba.python_root.nabu.db.KuzuConnectionManager.close -->
        │   │       ├─· close_all ● 0.02 <!-- nabu_nisaba.python_root.nabu.db.KuzuConnectionManager.close_all -->
        │   │       ├─· connection ● 0.01 <!-- nabu_nisaba.python_root.nabu.db.KuzuConnectionManager.connection -->
        │   │       ├─· execute ● 0.01 <!-- nabu_nisaba.python_root.nabu.db.KuzuConnectionManager.execute -->
        │   │       ├─· execute_async ● 0.01 <!-- nabu_nisaba.python_root.nabu.db.KuzuConnectionManager.execute_async -->
        │   │       └─· get_instance ● 0.01 <!-- nabu_nisaba.python_root.nabu.db.KuzuConnectionManager.get_instance -->
        │   ├─- embeddings <!-- nabu_nisaba.python_root.nabu.embeddings -->
        │   │   ├─+ BaseTransformerEmbeddingGenerator [5+] <!-- nabu_nisaba.python_root.nabu.embeddings.BaseTransformerEmbeddingGenerator -->
        │   │   ├─+ CodeBERTGenerator [5+] <!-- nabu_nisaba.python_root.nabu.embeddings.CodeBERTGenerator -->
        │   │   ├─+ EmbeddingGenerator [8+] <!-- nabu_nisaba.python_root.nabu.embeddings.EmbeddingGenerator -->
        │   │   ├─· EmbeddingModel <!-- nabu_nisaba.python_root.nabu.embeddings.EmbeddingModel -->
        │   │   ├─+ FusionStrategy [2+] <!-- nabu_nisaba.python_root.nabu.embeddings.FusionStrategy -->
        │   │   ├─+ NonLinearConsensusFusion [3+] <!-- nabu_nisaba.python_root.nabu.embeddings.NonLinearConsensusFusion -->
        │   │   ├─· SimilarityMetric <!-- nabu_nisaba.python_root.nabu.embeddings.SimilarityMetric -->
        │   │   ├─+ UniXcoderGenerator [5+] <!-- nabu_nisaba.python_root.nabu.embeddings.UniXcoderGenerator -->
        │   │   ├─· clear_generator_cache ● 0.02 <!-- nabu_nisaba.python_root.nabu.embeddings.clear_generator_cache -->
        │   │   ├─· compute_non_linear_consensus <!-- nabu_nisaba.python_root.nabu.embeddings.compute_non_linear_consensus -->
        │   │   ├─· get_codebert_generator <!-- nabu_nisaba.python_root.nabu.embeddings.get_codebert_generator -->
        │   │   ├─· get_model_cache_dir <!-- nabu_nisaba.python_root.nabu.embeddings.get_model_cache_dir -->
        │   │   └─· get_unixcoder_generator <!-- nabu_nisaba.python_root.nabu.embeddings.get_unixcoder_generator -->
        │   ├─+ exporter [1+] <!-- nabu_nisaba.python_root.nabu.exporter -->
        │   ├─- file_watcher <!-- nabu_nisaba.python_root.nabu.file_watcher -->
        │   │   ├─- FileChangeDebouncer <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeDebouncer -->
        │   │   │   ├─· __enter__ ● 0.01 <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeDebouncer.__enter__ -->
        │   │   │   ├─· __exit__ <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeDebouncer.__exit__ -->
        │   │   │   ├─· __init__ <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeDebouncer.__init__ -->
        │   │   │   ├─· _fire_callback <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeDebouncer._fire_callback -->
        │   │   │   ├─· _reset_timer <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeDebouncer._reset_timer -->
        │   │   │   ├─· add_change <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeDebouncer.add_change -->
        │   │   │   ├─· flush <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeDebouncer.flush -->
        │   │   │   └─· stop <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeDebouncer.stop -->
        │   │   ├─+ FileChangeEvent [2+] <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeEvent -->
        │   │   ├─· FileChangeType <!-- nabu_nisaba.python_root.nabu.file_watcher.FileChangeType -->
        │   │   ├─+ FileFilter [3+] <!-- nabu_nisaba.python_root.nabu.file_watcher.FileFilter -->
        │   │   └─- FileWatcher <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher -->
        │   │       ├─· __enter__ ● 0.01 <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher.__enter__ -->
        │   │       ├─· __exit__ <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher.__exit__ -->
        │   │       ├─· __init__ <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher.__init__ -->
        │   │       ├─· __repr__ <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher.__repr__ -->
        │   │       ├─· _execute_callback <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher._execute_callback -->
        │   │       ├─· _handle_event <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher._handle_event -->
        │   │       ├─· _process_batch <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher._process_batch -->
        │   │       ├─· is_running <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher.is_running -->
        │   │       ├─+ start [1+] <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher.start -->
        │   │       └─· stop <!-- nabu_nisaba.python_root.nabu.file_watcher.FileWatcher.stop -->
        │   ├─- incremental <!-- nabu_nisaba.python_root.nabu.incremental -->
        │   │   ├─- DatabaseMutator <!-- nabu_nisaba.python_root.nabu.incremental.DatabaseMutator -->
        │   │   │   ├─· __init__ ● 0.01 <!-- nabu_nisaba.python_root.nabu.incremental.DatabaseMutator.__init__ -->
        │   │   │   ├─· _extract_frame_data <!-- nabu_nisaba.python_root.nabu.incremental.DatabaseMutator._extract_frame_data -->
        │   │   │   ├─· delete_frames_by_id <!-- nabu_nisaba.python_root.nabu.incremental.DatabaseMutator.delete_frames_by_id -->
        │   │   │   ├─· insert_edges <!-- nabu_nisaba.python_root.nabu.incremental.DatabaseMutator.insert_edges -->
        │   │   │   ├─· insert_frames <!-- nabu_nisaba.python_root.nabu.incremental.DatabaseMutator.insert_frames -->
        │   │   │   └─· update_frame_content <!-- nabu_nisaba.python_root.nabu.incremental.DatabaseMutator.update_frame_content -->
        │   │   ├─· DeleteResult <!-- nabu_nisaba.python_root.nabu.incremental.DeleteResult -->
        │   │   ├─+ EdgeInserter [2+] <!-- nabu_nisaba.python_root.nabu.incremental.EdgeInserter -->
        │   │   ├─· EdgeInsertionResult <!-- nabu_nisaba.python_root.nabu.incremental.EdgeInsertionResult -->
        │   │   ├─+ FrameDiff [4+] <!-- nabu_nisaba.python_root.nabu.incremental.FrameDiff -->
        │   │   ├─- IncrementalUpdater <!-- nabu_nisaba.python_root.nabu.incremental.IncrementalUpdater -->
        │   │   │   ├─· __enter__ ● 0.01 <!-- nabu_nisaba.python_root.nabu.incremental.IncrementalUpdater.__enter__ -->
        │   │   │   ├─· __exit__ <!-- nabu_nisaba.python_root.nabu.incremental.IncrementalUpdater.__exit__ -->
        │   │   │   ├─· __init__ <!-- nabu_nisaba.python_root.nabu.incremental.IncrementalUpdater.__init__ -->
        │   │   │   ├─· _generate_warnings <!-- nabu_nisaba.python_root.nabu.incremental.IncrementalUpdater._generate_warnings -->
        │   │   │   ├─· _query_frames_by_file <!-- nabu_nisaba.python_root.nabu.incremental.IncrementalUpdater._query_frames_by_file -->
        │   │   │   ├─· close <!-- nabu_nisaba.python_root.nabu.incremental.IncrementalUpdater.close -->
        │   │   │   └─· update_file <!-- nabu_nisaba.python_root.nabu.incremental.IncrementalUpdater.update_file -->
        │   │   ├─· InsertEdgeResult <!-- nabu_nisaba.python_root.nabu.incremental.InsertEdgeResult -->
        │   │   ├─· InsertResult <!-- nabu_nisaba.python_root.nabu.incremental.InsertResult -->
        │   │   ├─+ RelationshipRepairer [24+] <!-- nabu_nisaba.python_root.nabu.incremental.RelationshipRepairer -->
        │   │   ├─· RepairResult <!-- nabu_nisaba.python_root.nabu.incremental.RepairResult -->
        │   │   ├─+ StableDiffCalculator [2+] <!-- nabu_nisaba.python_root.nabu.incremental.StableDiffCalculator -->
        │   │   ├─· UpdateMetric <!-- nabu_nisaba.python_root.nabu.incremental.UpdateMetric -->
        │   │   ├─+ UpdateMetricsCollector [13+] <!-- nabu_nisaba.python_root.nabu.incremental.UpdateMetricsCollector -->
        │   │   ├─+ UpdateResult [3+] <!-- nabu_nisaba.python_root.nabu.incremental.UpdateResult -->
        │   │   ├─· get_global_collector <!-- nabu_nisaba.python_root.nabu.incremental.get_global_collector -->
        │   │   ├─· get_statistics <!-- nabu_nisaba.python_root.nabu.incremental.get_statistics -->
        │   │   ├─· print_summary <!-- nabu_nisaba.python_root.nabu.incremental.print_summary -->
        │   │   └─· record_update ● 0.02 <!-- nabu_nisaba.python_root.nabu.incremental.record_update -->
        │   ├─+ language_handlers [9+] <!-- nabu_nisaba.python_root.nabu.language_handlers -->
        │   ├─- mcp <!-- nabu_nisaba.python_root.nabu.mcp -->
        │   │   ├─+ config [3+] <!-- nabu_nisaba.python_root.nabu.mcp.config -->
        │   │   ├─+ formatters [11+] <!-- nabu_nisaba.python_root.nabu.mcp.formatters -->
        │   │   ├─+ indexing [3+] <!-- nabu_nisaba.python_root.nabu.mcp.indexing -->
        │   │   ├─+ tools [16+] <!-- nabu_nisaba.python_root.nabu.mcp.tools -->
        │   │   ├─+ utils [14+] <!-- nabu_nisaba.python_root.nabu.mcp.utils -->
        │   │   ├─+ NabuAgent [4+] <!-- nabu_nisaba.python_root.nabu.mcp.NabuAgent -->
        │   │   ├─+ NabuMCPFactory [6+] <!-- nabu_nisaba.python_root.nabu.mcp.NabuMCPFactory -->
        │   │   ├─+ NabuMCPFactorySingleProcess [12+] <!-- nabu_nisaba.python_root.nabu.mcp.NabuMCPFactorySingleProcess -->
        │   │   ├─· cli <!-- nabu_nisaba.python_root.nabu.mcp.cli -->
        │   │   ├─· context <!-- nabu_nisaba.python_root.nabu.mcp.context -->
        │   │   ├─· context_list <!-- nabu_nisaba.python_root.nabu.mcp.context_list -->
        │   │   ├─· context_show <!-- nabu_nisaba.python_root.nabu.mcp.context_show -->
        │   │   ├─· db <!-- nabu_nisaba.python_root.nabu.mcp.db -->
        │   │   ├─· db_health_check <!-- nabu_nisaba.python_root.nabu.mcp.db_health_check -->
        │   │   ├─· db_reindex ● 0.01 <!-- nabu_nisaba.python_root.nabu.mcp.db_reindex -->
        │   │   ├─· db_stats <!-- nabu_nisaba.python_root.nabu.mcp.db_stats -->
        │   │   ├─· main <!-- nabu_nisaba.python_root.nabu.mcp.main -->
        │   │   ├─· prompt <!-- nabu_nisaba.python_root.nabu.mcp.prompt -->
        │   │   ├─· prompt_show <!-- nabu_nisaba.python_root.nabu.mcp.prompt_show -->
        │   │   ├─· tools_info ● 0.01 <!-- nabu_nisaba.python_root.nabu.mcp.tools_info -->
        │   │   └─· tools_list <!-- nabu_nisaba.python_root.nabu.mcp.tools_list -->
        │   ├─+ parsing [6+] <!-- nabu_nisaba.python_root.nabu.parsing -->
        │   ├─+ scripts [1+] <!-- nabu_nisaba.python_root.nabu.scripts -->
        │   ├─+ services [8+] <!-- nabu_nisaba.python_root.nabu.services -->
        │   ├─+ tui [6+] <!-- nabu_nisaba.python_root.nabu.tui -->
        │   ├─+ CodebaseParser [7+] <!-- nabu_nisaba.python_root.nabu.CodebaseParser -->
        │   └─· parse_codebase <!-- nabu_nisaba.python_root.nabu.parse_codebase -->
        ├─- nisaba <!-- nabu_nisaba.python_root.nisaba -->
        │   ├─+ server [3+] <!-- nabu_nisaba.python_root.nisaba.server -->
        │   ├─+ tools [15+] <!-- nabu_nisaba.python_root.nisaba.tools -->
        │   ├─+ tui [2+] <!-- nabu_nisaba.python_root.nisaba.tui -->
        │   ├─+ utils [5+] <!-- nabu_nisaba.python_root.nisaba.utils -->
        │   ├─+ wrapper [15+] <!-- nabu_nisaba.python_root.nisaba.wrapper -->
        │   ├─+ Agent [3+] <!-- nabu_nisaba.python_root.nisaba.Agent -->
        │   ├─+ Augment [1+] <!-- nabu_nisaba.python_root.nisaba.Augment -->
        │   ├─- AugmentManager <!-- nabu_nisaba.python_root.nisaba.AugmentManager -->
        │   │   ├─· __init__ ● 0.01 <!-- nabu_nisaba.python_root.nisaba.AugmentManager.__init__ -->
        │   │   ├─· _compose_and_write <!-- nabu_nisaba.python_root.nisaba.AugmentManager._compose_and_write -->
        │   │   ├─· _generate_augment_tree <!-- nabu_nisaba.python_root.nisaba.AugmentManager._generate_augment_tree -->
        │   │   ├─· _load_augments_from_dir <!-- nabu_nisaba.python_root.nisaba.AugmentManager._load_augments_from_dir -->
        │   │   ├─· _match_pattern <!-- nabu_nisaba.python_root.nisaba.AugmentManager._match_pattern -->
        │   │   ├─· _parse_augment_file <!-- nabu_nisaba.python_root.nisaba.AugmentManager._parse_augment_file -->
        │   │   ├─· _rebuild_tool_associations <!-- nabu_nisaba.python_root.nisaba.AugmentManager._rebuild_tool_associations -->
        │   │   ├─· _resolve_dependencies <!-- nabu_nisaba.python_root.nisaba.AugmentManager._resolve_dependencies -->
        │   │   ├─· _update_augment_tree_cache <!-- nabu_nisaba.python_root.nisaba.AugmentManager._update_augment_tree_cache -->
        │   │   ├─· activate_augments <!-- nabu_nisaba.python_root.nisaba.AugmentManager.activate_augments -->
        │   │   ├─· deactivate_augments <!-- nabu_nisaba.python_root.nisaba.AugmentManager.deactivate_augments -->
        │   │   ├─· get_related_tools <!-- nabu_nisaba.python_root.nisaba.AugmentManager.get_related_tools -->
        │   │   ├─· learn_augment <!-- nabu_nisaba.python_root.nisaba.AugmentManager.learn_augment -->
        │   │   ├─· load_state <!-- nabu_nisaba.python_root.nisaba.AugmentManager.load_state -->
        │   │   ├─· pin_augment <!-- nabu_nisaba.python_root.nisaba.AugmentManager.pin_augment -->
        │   │   ├─· save_state <!-- nabu_nisaba.python_root.nisaba.AugmentManager.save_state -->
        │   │   ├─· show_augments <!-- nabu_nisaba.python_root.nisaba.AugmentManager.show_augments -->
        │   │   ├─· state_file ● 0.01 <!-- nabu_nisaba.python_root.nisaba.AugmentManager.state_file -->
        │   │   └─· unpin_augment <!-- nabu_nisaba.python_root.nisaba.AugmentManager.unpin_augment -->
        │   ├─+ AutoRegisteringGroup [1+] <!-- nabu_nisaba.python_root.nisaba.AutoRegisteringGroup -->
        │   ├─+ ContextCommandGroup [2+] <!-- nabu_nisaba.python_root.nisaba.ContextCommandGroup -->
        │   ├─+ GuidanceGraph [1+] <!-- nabu_nisaba.python_root.nisaba.GuidanceGraph -->
        │   ├─+ GuidancePattern [1+] <!-- nabu_nisaba.python_root.nisaba.GuidancePattern -->
        │   ├─+ InstructionsTemplateEngine [9+] <!-- nabu_nisaba.python_root.nisaba.InstructionsTemplateEngine -->
        │   ├─+ MCPConfig [1+] <!-- nabu_nisaba.python_root.nisaba.MCPConfig -->
        │   ├─- MCPContext <!-- nabu_nisaba.python_root.nisaba.MCPContext -->
        │   │   ├─· from_yaml ● 0.01 <!-- nabu_nisaba.python_root.nisaba.MCPContext.from_yaml -->
        │   │   ├─· load <!-- nabu_nisaba.python_root.nisaba.MCPContext.load -->
        │   │   └─· load_default <!-- nabu_nisaba.python_root.nisaba.MCPContext.load_default -->
        │   ├─- MCPFactory <!-- nabu_nisaba.python_root.nisaba.MCPFactory -->
        │   │   ├─· __init__ <!-- nabu_nisaba.python_root.nisaba.MCPFactory.__init__ -->
        │   │   ├─· _create_typed_wrapper ● 0.01 <!-- nabu_nisaba.python_root.nisaba.MCPFactory._create_typed_wrapper -->
        │   │   ├─· _filter_enabled_tools ● 0.01 <!-- nabu_nisaba.python_root.nisaba.MCPFactory._filter_enabled_tools -->
        │   │   ├─· _generate_tool_documentation <!-- nabu_nisaba.python_root.nisaba.MCPFactory._generate_tool_documentation -->
        │   │   ├─· _get_initial_instructions <!-- nabu_nisaba.python_root.nisaba.MCPFactory._get_initial_instructions -->
        │   │   ├─· _get_module_prefix <!-- nabu_nisaba.python_root.nisaba.MCPFactory._get_module_prefix -->
        │   │   ├─· _get_registry_path <!-- nabu_nisaba.python_root.nisaba.MCPFactory._get_registry_path -->
        │   │   ├─· _get_tool_base_class <!-- nabu_nisaba.python_root.nisaba.MCPFactory._get_tool_base_class -->
        │   │   ├─· _get_tool_lock ● 0.01 <!-- nabu_nisaba.python_root.nisaba.MCPFactory._get_tool_lock -->
        │   │   ├─· _http_lifespan <!-- nabu_nisaba.python_root.nisaba.MCPFactory._http_lifespan -->
        │   │   ├─· _iter_tools <!-- nabu_nisaba.python_root.nisaba.MCPFactory._iter_tools -->
        │   │   ├─· _load_template_engine <!-- nabu_nisaba.python_root.nisaba.MCPFactory._load_template_engine -->
        │   │   ├─· _register_to_discovery <!-- nabu_nisaba.python_root.nisaba.MCPFactory._register_to_discovery -->
        │   │   ├─· _register_tools <!-- nabu_nisaba.python_root.nisaba.MCPFactory._register_tools -->
        │   │   ├─· _run_http_server <!-- nabu_nisaba.python_root.nisaba.MCPFactory._run_http_server -->
        │   │   ├─· _start_http_transport_if_enabled <!-- nabu_nisaba.python_root.nisaba.MCPFactory._start_http_transport_if_enabled -->
        │   │   ├─· _stop_http_transport <!-- nabu_nisaba.python_root.nisaba.MCPFactory._stop_http_transport -->
        │   │   ├─· _unregister_from_discovery <!-- nabu_nisaba.python_root.nisaba.MCPFactory._unregister_from_discovery -->
        │   │   ├─· create_mcp_server <!-- nabu_nisaba.python_root.nisaba.MCPFactory.create_mcp_server -->
        │   │   └─· server_lifespan <!-- nabu_nisaba.python_root.nisaba.MCPFactory.server_lifespan -->
        │   ├─+ MCPServerRegistry [8+] <!-- nabu_nisaba.python_root.nisaba.MCPServerRegistry -->
        │   ├─+ MCPTool [16+] <!-- nabu_nisaba.python_root.nisaba.MCPTool -->
        │   ├─- OutputFormat <!-- nabu_nisaba.python_root.nisaba.OutputFormat -->
        │   │   ├─· format_json <!-- nabu_nisaba.python_root.nisaba.OutputFormat.format_json -->
        │   │   ├─· format_yaml <!-- nabu_nisaba.python_root.nisaba.OutputFormat.format_yaml -->
        │   │   ├─· print_error <!-- nabu_nisaba.python_root.nisaba.OutputFormat.print_error -->
        │   │   ├─· print_header ● 0.01 <!-- nabu_nisaba.python_root.nisaba.OutputFormat.print_header -->
        │   │   ├─· print_markdown ● 0.01 <!-- nabu_nisaba.python_root.nisaba.OutputFormat.print_markdown -->
        │   │   └─· print_separator <!-- nabu_nisaba.python_root.nisaba.OutputFormat.print_separator -->
        │   ├─- PromptCommandGroup <!-- nabu_nisaba.python_root.nisaba.PromptCommandGroup -->
        │   │   └─· __init__ ● 0.02 <!-- nabu_nisaba.python_root.nisaba.PromptCommandGroup.__init__ -->
        │   ├─· RegisteredTool <!-- nabu_nisaba.python_root.nisaba.RegisteredTool -->
        │   ├─- ToolDocumentationGenerator <!-- nabu_nisaba.python_root.nisaba.ToolDocumentationGenerator -->
        │   │   ├─· __init__ <!-- nabu_nisaba.python_root.nisaba.ToolDocumentationGenerator.__init__ -->
        │   │   ├─· _default_categorize ● 0.01 <!-- nabu_nisaba.python_root.nisaba.ToolDocumentationGenerator._default_categorize -->
        │   │   ├─· format_tool_parameters ● 0.01 <!-- nabu_nisaba.python_root.nisaba.ToolDocumentationGenerator.format_tool_parameters -->
        │   │   └─· generate_documentation <!-- nabu_nisaba.python_root.nisaba.ToolDocumentationGenerator.generate_documentation -->
        │   ├─· ToolMarker <!-- nabu_nisaba.python_root.nisaba.ToolMarker -->
        │   ├─· ToolMarkerDevOnly <!-- nabu_nisaba.python_root.nisaba.ToolMarkerDevOnly -->
        │   ├─· ToolMarkerMutating <!-- nabu_nisaba.python_root.nisaba.ToolMarkerMutating -->
        │   ├─· ToolMarkerOptional <!-- nabu_nisaba.python_root.nisaba.ToolMarkerOptional -->
        │   ├─+ ToolRegistry [10+] <!-- nabu_nisaba.python_root.nisaba.ToolRegistry -->
        │   ├─- ToolsCommandGroup <!-- nabu_nisaba.python_root.nisaba.ToolsCommandGroup -->
        │   │   ├─· __init__ <!-- nabu_nisaba.python_root.nisaba.ToolsCommandGroup.__init__ -->
        │   │   └─· tool_registry ● 0.01 <!-- nabu_nisaba.python_root.nisaba.ToolsCommandGroup.tool_registry -->
        │   ├─- WorkflowGuidance <!-- nabu_nisaba.python_root.nisaba.WorkflowGuidance -->
        │   │   ├─· __init__ <!-- nabu_nisaba.python_root.nisaba.WorkflowGuidance.__init__ -->
        │   │   ├─· _get_augment_based_suggestion ● 0.02 <!-- nabu_nisaba.python_root.nisaba.WorkflowGuidance._get_augment_based_suggestion -->
        │   │   ├─· check_redundancy <!-- nabu_nisaba.python_root.nisaba.WorkflowGuidance.check_redundancy -->
        │   │   ├─· clear <!-- nabu_nisaba.python_root.nisaba.WorkflowGuidance.clear -->
        │   │   ├─· get_session_summary <!-- nabu_nisaba.python_root.nisaba.WorkflowGuidance.get_session_summary -->
        │   │   ├─· get_suggestions <!-- nabu_nisaba.python_root.nisaba.WorkflowGuidance.get_suggestions -->
        │   │   └─· record_tool_call <!-- nabu_nisaba.python_root.nisaba.WorkflowGuidance.record_tool_call -->
        │   ├─· augments <!-- nabu_nisaba.python_root.nisaba.augments -->
        │   ├─· augments_activate <!-- nabu_nisaba.python_root.nisaba.augments_activate -->
        │   ├─· augments_deactivate <!-- nabu_nisaba.python_root.nisaba.augments_deactivate -->
        │   ├─· augments_list <!-- nabu_nisaba.python_root.nisaba.augments_list -->
        │   ├─· cli <!-- nabu_nisaba.python_root.nisaba.cli -->
        │   ├─· format_context_list ● 0.02 <!-- nabu_nisaba.python_root.nisaba.format_context_list -->
        │   ├─· format_tool_list ● 0.02 <!-- nabu_nisaba.python_root.nisaba.format_tool_list -->
        │   ├─+ sanitize_for_openai_tools [1+] ● 0.02 <!-- nabu_nisaba.python_root.nisaba.sanitize_for_openai_tools -->
        │   ├─· servers <!-- nabu_nisaba.python_root.nisaba.servers -->
        │   ├─· servers_list <!-- nabu_nisaba.python_root.nisaba.servers_list -->
        │   ├─· validate_dir_or_exit <!-- nabu_nisaba.python_root.nisaba.validate_dir_or_exit -->
        │   └─· validate_file_or_exit <!-- nabu_nisaba.python_root.nisaba.validate_file_or_exit -->
        ├─+ utils [3+] <!-- nabu_nisaba.python_root.utils -->
        ├─· extract_transcript <!-- extract_transcript -->
        └─· main <!-- main -->