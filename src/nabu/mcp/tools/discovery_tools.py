"""Discovery and exploration tools for nabu MCP."""

from pathlib import Path
from typing import Any, Dict, List
import time

from nabu.mcp.tools.base import NabuTool
from nisaba.utils.response import ErrorSeverity


class MapCodebaseTool(NabuTool):
    """Get high-level project overview."""
    
    async def execute(self) -> Dict[str, Any]:
        """
        Get a comprehensive project overview.
        
        This should be the FIRST tool you call when starting work on a project.
        Provides the "lay of the land" without requiring you to know what to ask.
        
        Returns:
        - Project statistics (frame counts, language breakdown)
        - Top packages by size
        - Entry points (main functions)
        - Most connected classes (by degree centrality)
        - Suggested next steps
        
        :meta pitch: START HERE! Get the lay of the land instantly. No parameters needed - just run it and get oriented.
        :meta when: First tool to call in any new codebase
        :meta emoji: 🎯
        :meta tips: **Interpreting Results:**
            - **Top packages** - Focus on packages with high child_count, these are central to the codebase
            - **Entry points** - Look for main(), start(), create_* functions to understand how the application boots
            - **Most connected classes** - High connection count indicates architectural importance; these are good targets for `show_structure()`
            - **Suggested next steps** - Follow these recommendations for efficient exploration
        :meta examples: **Common Follow-up Queries:**

            After running explore_project(), use these queries to dig deeper:

            Explore a top package:
            ```python
            show_structure(target="<TopClassFromResults>")
            ```

            Find all classes in a top package:
            ```python
            query('''
            MATCH (p:Frame {qualified_name: "package.name"})-[:Edge {type: "CONTAINS"}*]->(c:Frame {type: "CLASS"})
            RETURN c.name, c.qualified_name
            LIMIT 20
            ''')
            ```

            Examine entry point dependencies:
            ```python
            query('''
            MATCH (entry:Frame {qualified_name: "main"})-[:Edge {type: "CALLS"}]->(called:Frame)
            RETURN called.name, called.type
            LIMIT 20
            ''')
            ```
        :return: JSON with project statistics, top packages, entry points, and most connected classes
        """
        start_time = time.time()
        
        try:
            # Check indexing status before proceeding
            indexing_check = self._check_indexing_status()
            if indexing_check:
                return indexing_check

            if self.db_manager is None:
                return self._error_response(
                    RuntimeError("Database manager not initialized"),
                    start_time,
                    severity=ErrorSeverity.FATAL,
                    recovery_hint="Database not initialized. Check db_path and restart MCP server."
                )
            
            # Query 1: Overall statistics
            stats_query = """
            MATCH (f:Frame)
            RETURN 
                count(*) as total_frames,
                count(DISTINCT f.file_path) as total_files,
                count(DISTINCT f.language) as language_count
            """
            stats_result = self.db_manager.execute(stats_query)
            stats_df = stats_result.get_as_df()
            
            # Query 2: Language breakdown
            lang_query = """
            MATCH (f:Frame)
            WHERE f.language IS NOT NULL
            RETURN 
                f.language,
                count(*) as frame_count,
                count(DISTINCT f.file_path) as file_count
            ORDER BY frame_count DESC
            """
            lang_result = self.db_manager.execute(lang_query)
            lang_df = lang_result.get_as_df()
            
            # Query 3: All packages (for stratified sampling)
            pkg_query = """
            MATCH (p:Frame {type: 'PACKAGE'})
            OPTIONAL MATCH (p)-[:Edge {type: 'CONTAINS'}]->(child:Frame)
            WITH p, count(child) as child_count
            RETURN
                p.id as id,
                p.name as package_name,
                p.qualified_name as qualified_name,
                p.file_path as file_path,
                child_count
            ORDER BY child_count DESC
            """
            pkg_result = self.db_manager.execute(pkg_query)
            pkg_df = pkg_result.get_as_df()
            
            # Query 4: Entry points
            entry_query = """
            MATCH (f:Frame {type: 'CALLABLE'})
            WHERE f.name IN ['main', '__main__', 'run', 'start', 'execute']
               OR f.name STARTS WITH 'create_'
            RETURN
                f.id as id,
                f.name as name,
                f.qualified_name as qualified_name,
                f.file_path as file_path,
                f.start_line as start_line,
                f.end_line as end_line
            LIMIT 10
            """
            entry_result = self.db_manager.execute(entry_query)
            entry_df = entry_result.get_as_df()
            
            # Query 5: All connected classes (for stratified sampling)
            central_query = """
            MATCH (c:Frame {type: 'CLASS'})
            OPTIONAL MATCH (c)<-[e_in:Edge]-(caller:Frame)
            OPTIONAL MATCH (c)-[e_out:Edge]->(callee:Frame)
            WITH c, count(DISTINCT e_in) as in_degree, count(DISTINCT e_out) as out_degree
            WITH c, in_degree, out_degree, (in_degree + out_degree) as total_degree
            WHERE total_degree > 0
            RETURN
                c.id as id,
                c.name as name,
                c.qualified_name as qualified_name,
                c.file_path as file_path,
                c.start_line as start_line,
                c.end_line as end_line,
                in_degree,
                out_degree,
                total_degree
            ORDER BY total_degree DESC
            """
            central_result = self.db_manager.execute(central_query)
            central_df = central_result.get_as_df()

            # Query 6: Relationship edge counts
            edge_query = """
            MATCH ()-[e:Edge]->()
            WITH e.type as edge_type, count(*) as edge_count
            RETURN edge_type, edge_count
            ORDER BY edge_count DESC
            """
            edge_result = self.db_manager.execute(edge_query)
            edge_df = edge_result.get_as_df()

            # Build response
            data = {
                "project_stats": {
                    "total_frames": int(stats_df.iloc[0]['total_frames']) if not stats_df.empty else 0,
                    "total_files": int(stats_df.iloc[0]['total_files']) if not stats_df.empty else 0,
                    "language_count": int(stats_df.iloc[0]['language_count']) if not stats_df.empty else 0,
                    "languages": {}
                },
                "top_packages": [],
                "entry_points": [],
                "most_connected_classes": [],
                "relationship_summary": {}
            }
            
            # Language breakdown
            for _, row in lang_df.iterrows():
                lang = row['f.language']
                data["project_stats"]["languages"][lang] = {
                    "frames": int(row['frame_count']),
                    "files": int(row['file_count'])
                }
            
            # Top packages
            for _, row in pkg_df.iterrows():
                data["top_packages"].append({
                    "id": row['id'],
                    "name": row['package_name'],
                    "qualified_name": row['qualified_name'],
                    "file_path": row['file_path'],
                    "child_count": int(row['child_count'])
                })
            
            # Entry points
            for _, row in entry_df.iterrows():
                data["entry_points"].append({
                    "id": row['id'],
                    "name": row['name'],
                    "qualified_name": row['qualified_name'],
                    "location": f"{Path(row['file_path']).name}:{row['start_line']}-{row['end_line']}",
                    "file_path": row['file_path']
                })
            
            # Most connected classes
            for _, row in central_df.iterrows():
                data["most_connected_classes"].append({
                    "id": row['id'],
                    "name": row['name'],
                    "qualified_name": row['qualified_name'],
                    "location": f"{Path(row['file_path']).name}:{row['start_line']}-{row['end_line']}",
                    "file_path": row['file_path'],
                    "incoming_edges": int(row['in_degree']),
                    "outgoing_edges": int(row['out_degree']),
                    "total_connections": int(row['total_degree'])
                })

            # Relationship summary
            for _, row in edge_df.iterrows():
                edge_type = row['edge_type']
                data["relationship_summary"][edge_type] = int(row['edge_count'])

            return self._success_response(data, start_time)
            
        except Exception as e:
            self.logger.error(f"Project exploration failed: {e}", exc_info=True)
            return self._error_response(
                e,
                start_time,
                recovery_hint=(
                    "Failed to explore project. Verify: "
                    "(1) Database is initialized (try show_status()), "
                    "(2) Database contains data (try rebuild_database() if empty)."
                ),
                context={"error_type": type(e).__name__}
            )
