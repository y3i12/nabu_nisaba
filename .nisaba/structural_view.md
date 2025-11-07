**search query**: "editor"

- nabu_nisaba <!-- nabu_nisaba -->
    ├─- cpp_root <!-- nabu_nisaba.cpp_root -->
    │   ├─- core <!-- nabu_nisaba.cpp_root::core -->
    │   │   ├─+ BaseProcessor [2+] <!-- nabu_nisaba.cpp_root::core.BaseProcessor -->
    │   │   ├─+ DataProcessor [3+] <!-- nabu_nisaba.cpp_root::core.DataProcessor -->
    │   │   ├─· BaseProcessor ● 0.01 <!-- nabu_nisaba.cpp_root::core.BaseProcessor.BaseProcessor -->
    │   │   ├─· DataProcessor ● 0.01 <!-- nabu_nisaba.cpp_root::core.DataProcessor.DataProcessor -->
    │   │   ├─· getStats ● 0.01 <!-- nabu_nisaba.cpp_root::core.DataProcessor.getStats -->
    │   │   ├─· process ● 0.01 <!-- nabu_nisaba.cpp_root::core.DataProcessor.process -->
    │   │   └─· ~BaseProcessor ● 0.01 <!-- nabu_nisaba.cpp_root::core.BaseProcessor.~BaseProcessor -->
    │   └─- utils <!-- nabu_nisaba.cpp_root::utils -->
    │       ├─+ Helper [2+] <!-- nabu_nisaba.cpp_root::utils.Helper -->
    │       ├─+ Logger [3+] <!-- nabu_nisaba.cpp_root::utils.Logger -->
    │       ├─· Logger ● 0.01 <!-- nabu_nisaba.cpp_root::utils.Logger.Logger -->
    │       ├─· disable ● 0.01 <!-- nabu_nisaba.cpp_root::utils.Logger.disable -->
    │       ├─· formatOutput ● 0.01 <!-- nabu_nisaba.cpp_root::utils.Helper.formatOutput -->
    │       ├─· log <!-- nabu_nisaba.cpp_root::utils.Logger.log -->
    │       └─· validateInput <!-- nabu_nisaba.cpp_root::utils.Helper.validateInput -->
    ├─+ java_root [1+] <!-- nabu_nisaba.java_root -->
    ├─- perl_root <!-- nabu_nisaba.perl_root -->
    │   ├─- Core <!-- nabu_nisaba.perl_root::Core -->
    │   │   ├─· get_stats ● 0.01 <!-- nabu_nisaba.perl_root::Core.get_stats -->
    │   │   ├─· new <!-- nabu_nisaba.perl_root::Core.new -->
    │   │   └─· process <!-- nabu_nisaba.perl_root::Core.process -->
    │   └─+ Utils [5+] <!-- nabu_nisaba.perl_root::Utils -->
    └─- python_root <!-- nabu_nisaba.python_root -->
        ├─+ core [2+] <!-- nabu_nisaba.python_root.core -->
        ├─- nabu <!-- nabu_nisaba.python_root.nabu -->
        │   ├─- core <!-- nabu_nisaba.python_root.nabu.core -->
        │   │   ├─+ AstCallableFrame [1+] <!-- nabu_nisaba.python_root.nabu.core.AstCallableFrame -->
        │   │   ├─+ AstClassFrame [1+] <!-- nabu_nisaba.python_root.nabu.core.AstClassFrame -->
        │   │   ├─+ AstCodebaseFrame [1+] <!-- nabu_nisaba.python_root.nabu.core.AstCodebaseFrame -->
        │   │   ├─+ AstEdge [1+] <!-- nabu_nisaba.python_root.nabu.core.AstEdge -->
        │   │   ├─+ AstFrameBase [22+] <!-- nabu_nisaba.python_root.nabu.core.AstFrameBase -->
        │   │   ├─+ AstLanguageFrame [1+] <!-- nabu_nisaba.python_root.nabu.core.AstLanguageFrame -->
        │   │   ├─+ AstPackageFrame [1+] <!-- nabu_nisaba.python_root.nabu.core.AstPackageFrame -->
        │   │   ├─· AstVariableFrame <!-- nabu_nisaba.python_root.nabu.core.AstVariableFrame -->
        │   │   ├─+ CodebaseContext [5+] <!-- nabu_nisaba.python_root.nabu.core.CodebaseContext -->
        │   │   ├─+ ConfidenceCalculator [4+] <!-- nabu_nisaba.python_root.nabu.core.ConfidenceCalculator -->
        │   │   ├─+ ConfidenceContext [4+] <!-- nabu_nisaba.python_root.nabu.core.ConfidenceContext -->
        │   │   ├─· ConfidenceTier <!-- nabu_nisaba.python_root.nabu.core.ConfidenceTier -->
        │   │   ├─+ DatabaseResolutionStrategy [7+] <!-- nabu_nisaba.python_root.nabu.core.DatabaseResolutionStrategy -->
        │   │   ├─· EdgeType <!-- nabu_nisaba.python_root.nabu.core.EdgeType -->
        │   │   ├─+ FieldInfo [1+] <!-- nabu_nisaba.python_root.nabu.core.FieldInfo -->
        │   │   ├─+ FrameNodeType [7+] <!-- nabu_nisaba.python_root.nabu.core.FrameNodeType -->
        │   │   ├─+ FrameRegistry [17+] <!-- nabu_nisaba.python_root.nabu.core.FrameRegistry -->
        │   │   ├─+ FrameStack [22+] <!-- nabu_nisaba.python_root.nabu.core.FrameStack -->
        │   │   ├─+ IdStabilityMetrics [2+] <!-- nabu_nisaba.python_root.nabu.core.IdStabilityMetrics -->
        │   │   ├─· IdStrategy <!-- nabu_nisaba.python_root.nabu.core.IdStrategy -->
        │   │   ├─+ MemoryResolutionStrategy [8+] <!-- nabu_nisaba.python_root.nabu.core.MemoryResolutionStrategy -->
        │   │   ├─· NodeContext <!-- nabu_nisaba.python_root.nabu.core.NodeContext -->
        │   │   ├─+ ParameterInfo [1+] <!-- nabu_nisaba.python_root.nabu.core.ParameterInfo -->
        │   │   ├─+ ResolutionResult [1+] <!-- nabu_nisaba.python_root.nabu.core.ResolutionResult -->
        │   │   ├─+ ResolutionStrategy [6+] <!-- nabu_nisaba.python_root.nabu.core.ResolutionStrategy -->
        │   │   ├─+ SkeletonBuilder [6+] <!-- nabu_nisaba.python_root.nabu.core.SkeletonBuilder -->
        │   │   ├─+ SkeletonFormatter [1+] <!-- nabu_nisaba.python_root.nabu.core.SkeletonFormatter -->
        │   │   ├─· SkeletonOptions <!-- nabu_nisaba.python_root.nabu.core.SkeletonOptions -->
        │   │   ├─+ StableIdGenerator [10+] <!-- nabu_nisaba.python_root.nabu.core.StableIdGenerator -->
        │   │   ├─+ _extract_control_flows_from_ast [1+] ● 0.01 <!-- nabu_nisaba.python_root.nabu.core._extract_control_flows_from_ast -->
        │   │   ├─· _extract_name_from_node <!-- nabu_nisaba.python_root.nabu.core._extract_name_from_node -->
        │   │   ├─· _get_formatter_registry <!-- nabu_nisaba.python_root.nabu.core._get_formatter_registry -->
        │   │   ├─· adjust_field_usage_confidence ● 0.01 <!-- nabu_nisaba.python_root.nabu.core.adjust_field_usage_confidence -->
        │   │   ├─· create_node_context_from_raw_node <!-- nabu_nisaba.python_root.nabu.core.create_node_context_from_raw_node -->
        │   │   ├─· extract_cpp_class_from_signature <!-- nabu_nisaba.python_root.nabu.core.extract_cpp_class_from_signature -->
        │   │   └─· extract_semantic_anchor <!-- nabu_nisaba.python_root.nabu.core.extract_semantic_anchor -->
        │   ├─+ db [1+] <!-- nabu_nisaba.python_root.nabu.db -->
        │   ├─+ embeddings [13+] <!-- nabu_nisaba.python_root.nabu.embeddings -->
        │   ├─+ exporter [1+] <!-- nabu_nisaba.python_root.nabu.exporter -->
        │   ├─+ file_watcher [5+] <!-- nabu_nisaba.python_root.nabu.file_watcher -->
        │   ├─- incremental <!-- nabu_nisaba.python_root.nabu.incremental -->
        │   │   ├─+ DatabaseMutator [6+] <!-- nabu_nisaba.python_root.nabu.incremental.DatabaseMutator -->
        │   │   ├─· DeleteResult <!-- nabu_nisaba.python_root.nabu.incremental.DeleteResult -->
        │   │   ├─+ EdgeInserter [2+] <!-- nabu_nisaba.python_root.nabu.incremental.EdgeInserter -->
        │   │   ├─· EdgeInsertionResult <!-- nabu_nisaba.python_root.nabu.incremental.EdgeInsertionResult -->
        │   │   ├─+ FrameDiff [4+] <!-- nabu_nisaba.python_root.nabu.incremental.FrameDiff -->
        │   │   ├─+ IncrementalUpdater [7+] <!-- nabu_nisaba.python_root.nabu.incremental.IncrementalUpdater -->
        │   │   ├─· InsertEdgeResult <!-- nabu_nisaba.python_root.nabu.incremental.InsertEdgeResult -->
        │   │   ├─· InsertResult <!-- nabu_nisaba.python_root.nabu.incremental.InsertResult -->
        │   │   ├─+ RelationshipRepairer [24+] <!-- nabu_nisaba.python_root.nabu.incremental.RelationshipRepairer -->
        │   │   ├─· RepairResult <!-- nabu_nisaba.python_root.nabu.incremental.RepairResult -->
        │   │   ├─+ StableDiffCalculator [2+] <!-- nabu_nisaba.python_root.nabu.incremental.StableDiffCalculator -->
        │   │   ├─· UpdateMetric <!-- nabu_nisaba.python_root.nabu.incremental.UpdateMetric -->
        │   │   ├─+ UpdateMetricsCollector [13+] <!-- nabu_nisaba.python_root.nabu.incremental.UpdateMetricsCollector -->
        │   │   ├─+ UpdateResult [3+] <!-- nabu_nisaba.python_root.nabu.incremental.UpdateResult -->
        │   │   ├─· get_global_collector ● 0.01 <!-- nabu_nisaba.python_root.nabu.incremental.get_global_collector -->
        │   │   ├─· get_statistics ● 0.01 <!-- nabu_nisaba.python_root.nabu.incremental.get_statistics -->
        │   │   ├─· print_summary ● 0.01 <!-- nabu_nisaba.python_root.nabu.incremental.print_summary -->
        │   │   └─· record_update ● 0.01 <!-- nabu_nisaba.python_root.nabu.incremental.record_update -->
        │   ├─+ language_handlers [9+] <!-- nabu_nisaba.python_root.nabu.language_handlers -->
        │   ├─- mcp <!-- nabu_nisaba.python_root.nabu.mcp -->
        │   │   ├─+ config [3+] <!-- nabu_nisaba.python_root.nabu.mcp.config -->
        │   │   ├─+ formatters [11+] <!-- nabu_nisaba.python_root.nabu.mcp.formatters -->
        │   │   ├─+ indexing [3+] <!-- nabu_nisaba.python_root.nabu.mcp.indexing -->
        │   │   ├─+ tools [16+] ● 0.01 <!-- nabu_nisaba.python_root.nabu.mcp.tools -->
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
        │   │   ├─· db_reindex <!-- nabu_nisaba.python_root.nabu.mcp.db_reindex -->
        │   │   ├─· db_stats <!-- nabu_nisaba.python_root.nabu.mcp.db_stats -->
        │   │   ├─· main <!-- nabu_nisaba.python_root.nabu.mcp.main -->
        │   │   ├─· prompt <!-- nabu_nisaba.python_root.nabu.mcp.prompt -->
        │   │   ├─· prompt_show <!-- nabu_nisaba.python_root.nabu.mcp.prompt_show -->
        │   │   ├─· tools_info <!-- nabu_nisaba.python_root.nabu.mcp.tools_info -->
        │   │   └─· tools_list <!-- nabu_nisaba.python_root.nabu.mcp.tools_list -->
        │   ├─+ parsing [6+] <!-- nabu_nisaba.python_root.nabu.parsing -->
        │   ├─+ scripts [1+] <!-- nabu_nisaba.python_root.nabu.scripts -->
        │   ├─+ services [8+] <!-- nabu_nisaba.python_root.nabu.services -->
        │   ├─+ tui [6+] <!-- nabu_nisaba.python_root.nabu.tui -->
        │   ├─- CodebaseParser <!-- nabu_nisaba.python_root.nabu.CodebaseParser -->
        │   │   ├─· __init__ ● 0.01 <!-- nabu_nisaba.python_root.nabu.CodebaseParser.__init__ -->
        │   │   ├─· _collect_structural_info <!-- nabu_nisaba.python_root.nabu.CodebaseParser._collect_structural_info -->
        │   │   ├─+ _count_frames [1+] <!-- nabu_nisaba.python_root.nabu.CodebaseParser._count_frames -->
        │   │   ├─· export_to_kuzu <!-- nabu_nisaba.python_root.nabu.CodebaseParser.export_to_kuzu -->
        │   │   ├─· get_parsing_statistics <!-- nabu_nisaba.python_root.nabu.CodebaseParser.get_parsing_statistics -->
        │   │   ├─· parse_codebase <!-- nabu_nisaba.python_root.nabu.CodebaseParser.parse_codebase -->
        │   │   └─· parse_single_file <!-- nabu_nisaba.python_root.nabu.CodebaseParser.parse_single_file -->
        │   └─· parse_codebase ● 0.02 <!-- nabu_nisaba.python_root.nabu.parse_codebase -->
        ├─- nisaba <!-- nabu_nisaba.python_root.nisaba -->
        │   ├─+ server [3+] <!-- nabu_nisaba.python_root.nisaba.server -->
        │   ├─- tools <!-- nabu_nisaba.python_root.nisaba.tools -->
        │   │   ├─+ ActivateAugmentsTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.ActivateAugmentsTool -->
        │   │   ├─+ DeactivateAugmentsTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.DeactivateAugmentsTool -->
        │   │   ├─- EditorTool ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tools.EditorTool -->
        │   │   │   ├─· __init__ <!-- nabu_nisaba.python_root.nisaba.tools.EditorTool.__init__ -->
        │   │   │   ├─· _error ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tools.EditorTool._error -->
        │   │   │   ├─· execute ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tools.EditorTool.execute -->
        │   │   │   └─· manager ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tools.EditorTool.manager -->
        │   │   ├─+ LearnAugmentTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.LearnAugmentTool -->
        │   │   ├─+ NisabaBashTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.NisabaBashTool -->
        │   │   ├─+ NisabaEditTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.NisabaEditTool -->
        │   │   ├─+ NisabaGlobTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.NisabaGlobTool -->
        │   │   ├─+ NisabaGrepTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.NisabaGrepTool -->
        │   │   ├─+ NisabaReadTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.NisabaReadTool -->
        │   │   ├─+ NisabaTodoWriteTool [4+] <!-- nabu_nisaba.python_root.nisaba.tools.NisabaTodoWriteTool -->
        │   │   ├─+ NisabaTool [5+] <!-- nabu_nisaba.python_root.nisaba.tools.NisabaTool -->
        │   │   ├─+ NisabaToolResultStateTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.NisabaToolResultStateTool -->
        │   │   ├─+ NisabaToolWindowsTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.NisabaToolWindowsTool -->
        │   │   ├─+ NisabaWriteTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.NisabaWriteTool -->
        │   │   ├─+ PinAugmentTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.PinAugmentTool -->
        │   │   └─+ UnpinAugmentTool [1+] <!-- nabu_nisaba.python_root.nisaba.tools.UnpinAugmentTool -->
        │   ├─- tui <!-- nabu_nisaba.python_root.nisaba.tui -->
        │   │   ├─· Edit <!-- nabu_nisaba.python_root.nisaba.tui.Edit -->
        │   │   ├─- EditorManager ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager -->
        │   │   │   ├─· __init__ ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.__init__ -->
        │   │   │   ├─· _add_notification <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager._add_notification -->
        │   │   │   ├─· _format_time_ago <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager._format_time_ago -->
        │   │   │   ├─· _generate_inline_diff <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager._generate_inline_diff -->
        │   │   │   ├─· _get_editor_by_id ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager._get_editor_by_id -->
        │   │   │   ├─· _write_to_disk ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager._write_to_disk -->
        │   │   │   ├─· close ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.close -->
        │   │   │   ├─· close_all ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.close_all -->
        │   │   │   ├─· close_split ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.close_split -->
        │   │   │   ├─· delete ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.delete -->
        │   │   │   ├─· insert ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.insert -->
        │   │   │   ├─· load_state ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.load_state -->
        │   │   │   ├─· open ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.open -->
        │   │   │   ├─· refresh_all ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.refresh_all -->
        │   │   │   ├─· render ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.render -->
        │   │   │   ├─· replace ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.replace -->
        │   │   │   ├─· replace_lines ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.replace_lines -->
        │   │   │   ├─· resize ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.resize -->
        │   │   │   ├─· save_state ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.save_state -->
        │   │   │   ├─· split ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.split -->
        │   │   │   ├─· status ● 0.02 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.status -->
        │   │   │   └─· write ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.EditorManager.write -->
        │   │   ├─- EditorWindow <!-- nabu_nisaba.python_root.nisaba.tui.EditorWindow -->
        │   │   │   ├─· from_dict ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.EditorWindow.from_dict -->
        │   │   │   ├─· is_dirty <!-- nabu_nisaba.python_root.nisaba.tui.EditorWindow.is_dirty -->
        │   │   │   └─· to_dict <!-- nabu_nisaba.python_root.nisaba.tui.EditorWindow.to_dict -->
        │   │   ├─- Split <!-- nabu_nisaba.python_root.nisaba.tui.Split -->
        │   │   │   ├─· from_dict ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.Split.from_dict -->
        │   │   │   └─· to_dict ● 0.01 <!-- nabu_nisaba.python_root.nisaba.tui.Split.to_dict -->
        │   │   ├─· ToolResultWindow <!-- nabu_nisaba.python_root.nisaba.tui.ToolResultWindow -->
        │   │   └─+ ToolResultWindowsManager [13+] <!-- nabu_nisaba.python_root.nisaba.tui.ToolResultWindowsManager -->
        │   ├─+ utils [5+] <!-- nabu_nisaba.python_root.nisaba.utils -->
        │   ├─+ wrapper [12+] <!-- nabu_nisaba.python_root.nisaba.wrapper -->
        │   ├─+ Agent [3+] <!-- nabu_nisaba.python_root.nisaba.Agent -->
        │   ├─+ Augment [1+] <!-- nabu_nisaba.python_root.nisaba.Augment -->
        │   ├─+ AugmentManager [19+] <!-- nabu_nisaba.python_root.nisaba.AugmentManager -->
        │   ├─+ AutoRegisteringGroup [1+] <!-- nabu_nisaba.python_root.nisaba.AutoRegisteringGroup -->
        │   ├─+ ContextCommandGroup [2+] <!-- nabu_nisaba.python_root.nisaba.ContextCommandGroup -->
        │   ├─+ GuidanceGraph [1+] <!-- nabu_nisaba.python_root.nisaba.GuidanceGraph -->
        │   ├─+ GuidancePattern [1+] <!-- nabu_nisaba.python_root.nisaba.GuidancePattern -->
        │   ├─+ InstructionsTemplateEngine [9+] <!-- nabu_nisaba.python_root.nisaba.InstructionsTemplateEngine -->
        │   ├─+ MCPConfig [1+] <!-- nabu_nisaba.python_root.nisaba.MCPConfig -->
        │   ├─+ MCPContext [3+] <!-- nabu_nisaba.python_root.nisaba.MCPContext -->
        │   ├─+ MCPFactory [20+] <!-- nabu_nisaba.python_root.nisaba.MCPFactory -->
        │   ├─+ MCPServerRegistry [8+] <!-- nabu_nisaba.python_root.nisaba.MCPServerRegistry -->
        │   ├─+ MCPTool [16+] <!-- nabu_nisaba.python_root.nisaba.MCPTool -->
        │   ├─+ OutputFormat [6+] <!-- nabu_nisaba.python_root.nisaba.OutputFormat -->
        │   ├─+ PromptCommandGroup [1+] <!-- nabu_nisaba.python_root.nisaba.PromptCommandGroup -->
        │   ├─· RegisteredTool <!-- nabu_nisaba.python_root.nisaba.RegisteredTool -->
        │   ├─+ ToolDocumentationGenerator [4+] <!-- nabu_nisaba.python_root.nisaba.ToolDocumentationGenerator -->
        │   ├─· ToolMarker <!-- nabu_nisaba.python_root.nisaba.ToolMarker -->
        │   ├─· ToolMarkerDevOnly <!-- nabu_nisaba.python_root.nisaba.ToolMarkerDevOnly -->
        │   ├─· ToolMarkerMutating <!-- nabu_nisaba.python_root.nisaba.ToolMarkerMutating -->
        │   ├─· ToolMarkerOptional <!-- nabu_nisaba.python_root.nisaba.ToolMarkerOptional -->
        │   ├─+ ToolRegistry [10+] <!-- nabu_nisaba.python_root.nisaba.ToolRegistry -->
        │   ├─+ ToolsCommandGroup [2+] <!-- nabu_nisaba.python_root.nisaba.ToolsCommandGroup -->
        │   ├─+ WorkflowGuidance [7+] <!-- nabu_nisaba.python_root.nisaba.WorkflowGuidance -->
        │   ├─· augments <!-- nabu_nisaba.python_root.nisaba.augments -->
        │   ├─· augments_activate <!-- nabu_nisaba.python_root.nisaba.augments_activate -->
        │   ├─· augments_deactivate <!-- nabu_nisaba.python_root.nisaba.augments_deactivate -->
        │   ├─· augments_list ● 0.02 <!-- nabu_nisaba.python_root.nisaba.augments_list -->
        │   ├─· cli ● 0.02 <!-- nabu_nisaba.python_root.nisaba.cli -->
        │   ├─· format_context_list ● 0.02 <!-- nabu_nisaba.python_root.nisaba.format_context_list -->
        │   ├─· format_tool_list <!-- nabu_nisaba.python_root.nisaba.format_tool_list -->
        │   ├─+ sanitize_for_openai_tools [1+] <!-- nabu_nisaba.python_root.nisaba.sanitize_for_openai_tools -->
        │   ├─· servers <!-- nabu_nisaba.python_root.nisaba.servers -->
        │   ├─· servers_list <!-- nabu_nisaba.python_root.nisaba.servers_list -->
        │   ├─· validate_dir_or_exit ● 0.02 <!-- nabu_nisaba.python_root.nisaba.validate_dir_or_exit -->
        │   └─· validate_file_or_exit <!-- nabu_nisaba.python_root.nisaba.validate_file_or_exit -->
        ├─- utils <!-- nabu_nisaba.python_root.utils -->
        │   ├─+ Logger [3+] <!-- nabu_nisaba.python_root.utils.Logger -->
        │   ├─· format_output ● 0.02 <!-- nabu_nisaba.python_root.utils.format_output -->
        │   └─· validate_input <!-- nabu_nisaba.python_root.utils.validate_input -->
        ├─· extract_transcript <!-- extract_transcript -->
        └─· main <!-- main -->