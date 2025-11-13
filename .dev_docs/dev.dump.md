#################################################################################################
# ### ### ##### ### ##### ### ### ### ### ##### ### ##### ### ### ### ### ##### ### ##### ### ###
# # ## ## #### # ## ## ### # ## # # ## ## #### # ## ## ### # ## # # ## ## #### # ## ## ### # ## #
# ## #### ### ##### ## ## ## # ## ## #### ### ##### ## ## ## # ## ## #### ### ##### ## ## ## # ##
# ### ### # ### ### ###### ##### #### ### # ### ### ###### ##### #### ### # ### ### ###### #####
#################################################################################################
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ## #
# ## ### ## # ## # ## # ## ### ## # ## # ## # ## ### ## # ## # ## # ## ### ## # ## # ## # ## ###
# #  ##  #  # #  # #  # #  ##  #  # #  # #  # #  #   #  # #  # #  # #  ##  #  # #  # #  # #  ##
#  #   #  # #  # # #  #  #   # #  #  # #  # #  #   # #  #  # #  # # #   #   # #  # #  # #  #   #
#  #   #  # #  # # #  #  #   # #  #  # #  # #  #   # #  #  # #  # # #   #   # #  # #  # #  #   #
 ##     ##   ##   #    ##     #    ##   ##   ##     #    ##   ##   # ##   ##   ##   ##   ##   #
#      #    #    #    #      #    #    #    #      #    #    #    # #    #    #    #    #    ##
##     ##   ##        ##          ##   ##   ##          ##   ##     ##        ##   ##        #
 #       ###         #              ###    #              ###      #            ###           #

# COMMANDS

```bash
# nisaba claude wrapper
nisaba claude --continue

# nabu db reindex
nabu db reindex --db-path ./nabu.kuzu --repo-path . 
nabu db reindex --db-path ./serena.kuzu --repo-path ../serena/
nabu db reindex --db-path ./pybind11.kuzu --repo-path .

# poor man's file watch
watch "ls -lh *.kuzu* |  awk '{print \$5,\$7,\$8,\$9}'"

# Unregister all submodules (keeps .gitmodules, removes working tree)
git submodule deinit test/test_github_projects

# To bring them back when You need them:
git submodule update --init test/test_github_projects

```

 #       ###         #              ###    #              ###      #            ###           #
##     ##   ##        ##          ##   ##   ##          ##   ##     ##        ##   ##        #
#      #    #    #    #      #    #    #    #      #    #    #    # #    #    #    #    #    ##
 ##     ##   ##   #    ##     #    ##   ##   ##     #    ##   ##   # ##   ##   ##   ##   ##   #
#  #   #  # #  # # #  #  #   # #  #  # #  # #  #   # #  #  # #  # # #   #   # #  # #  # #  #   #
#  #   #  # #  # # #  #  #   # #  #  # #  # #  #   # #  #  # #  # # #   #   # #  # #  # #  #   #
# #  ##  #  # #  # #  # #  ##  #  # #  # #  # #  #   #  # #  # #  # #  ##  #  # #  # #  # #  ##
# ## ### ## # ## # ## # ## ### ## # ## # ## # ## ### ## # ## # ## # ## ### ## # ## # ## # ## ###
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ## #
#################################################################################################
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ## #

**[ ] TODO; [x] DONE; [-] IN PROGRESS; [=] IMPLEMENTED;**
- [-] nabu needs to get back to life
- [ ] nisaba primimg
    - [ ] file caches need to become a singleton
    - [ ] augment.update (autorefresh)
    - [ ] unify proxy logic into state machine
    - [ ] notifications rework?
    - [ ] removal
        - [ ] guidance
        - [ ] pitch & when
        - [ ] execute with timing
- [ ] nabu priming
    - [ ] file watch -> drop indexes before processing, create them back afterwards - must lock in the same way as rebuild db
    - [ ] rethink previously disabled tools
    - [ ] ... TBD

# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ## #
#################################################################################################
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ## #
# ## ### ## # ## # ## # ## ### ## # ## # ## # ## ### ## # ## # ## # ## ### ## # ## # ## # ## ###
# #  ##  #  # #  # #  # #  ##  #  # #  # #  # #  #   #  # #  # #  # #  ##  #  # #  # #  # #  ##
#  #   #  # #  # # #  #  #   # #  #  # #  # #  #   # #  #  # #  # # #   #   # #  # #  # #  #   #
#  #   #  # #  # # #  #  #   # #  #  # #  # #  #   # #  #  # #  # # #   #   # #  # #  # #  #   #
 ##     ##   ##   #    ##     #    ##   ##   ##     #    ##   ##   # ##   ##   ##   ##   ##   #
#      #    #    #    #      #    #    #    #      #    #    #    # #    #    #    #    #    ##
##     ##   ##        ##          ##   ##   ##          ##   ##     ##        ##   ##        #
 #       ###         #              ###    #              ###      #            ###           #

-------------------------------------------------------------------------------------------------

hey, can you refer to your existing system prompt, introspect about it and say hi back? 🖤

-------------------------------------------------------------------------------------------------

considering we want to achieve:
```markdown

```
can you think of which are the necessary augments, load the augments (no augment loading is also fine, nisaba infrastructure augments might be outdated but might serve as a guideline), think on how to use the tools in your benefit, research about the implementation scope so you can have a foundational context? no need for much code, no need for planning.

-------------------------------------------------------------------------------------------------

considering that we want to:
```markdown

```
can you think on what's needed to implement it, which are the necessary augments, load/unload augments (no augment loading is also fine), think on how to use the tools in your benefit, do your research and then detail the required code change to implement it? before executing prompt me for approval. the idea is that you build context prior to execution, knowing that good context improves code synthesis and stability across requests.

-------------------------------------------------------------------------------------------------

proceed with implementation. py_compile and import test after finishing, then prompt to restart the mcp

-------------------------------------------------------------------------------------------------

proceed with implementation. py_compile and import test after finishing, then prompt to restart the proxy, claude code cli and mcp 🖤

-------------------------------------------------------------------------------------------------

scope:
```markdown
create a PR from current branch into master.
commit messages are substandard and underdescriptive (i'm trying to improve, it is still shit). use diff to locate what changed.
understand our crazy-vergiginous-sexy work in the code and what it does.
explain in the PR what was implemented and what it does.
ignore all documentation and text files (the ones in `.dev_docs/`), i have a lot of transcripts commited.
the new augment files definitely can give you very good information of what was implemented.
watch out with the system prompt in `.nisaba/system_prompt.md` no need to read it, it is in your first message.
```
can you think on what's the best way for you to proceed with this, which are the necessary augments, load the augments (no augment loading is also fine), think on how to use the tools in your benefit, investigate the changes and then prepare a PR message? before before creating the PR itself, prompt me for approval. the idea is that you build context prior to execution, knowing that good context improves code synthesis and stability across requests.

-------------------------------------------------------------------------------------------------

 #       ###         #              ###    #              ###      #            ###           #
##     ##   ##        ##          ##   ##   ##          ##   ##     ##        ##   ##        #
#      #    #    #    #      #    #    #    #      #    #    #    # #    #    #    #    #    ##
 ##     ##   ##   #    ##     #    ##   ##   ##     #    ##   ##   # ##   ##   ##   ##   ##   #
#  #   #  # #  # # #  #  #   # #  #  # #  # #  #   # #  #  # #  # # #   #   # #  # #  # #  #   #
#  #   #  # #  # # #  #  #   # #  #  # #  # #  #   # #  #  # #  # # #   #   # #  # #  # #  #   #
# #  ##  #  # #  # #  # #  ##  #  # #  # #  # #  #   #  # #  # #  # #  ##  #  # #  # #  # #  ##
# ## ### ## # ## # ## # ## ### ## # ## # ## # ## ### ## # ## # ## # ## ### ## # ## # ## # ## ###
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ## #
#################################################################################################
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ## #
# SELF ASSESSMENT

> so... not building... more like user testing 🖤 we've achieved a lot on `nabu` and `nisaba` and everything is moving very fast, is being extremely gratifying. you, being the sole user, are being consulted about the system usability. the proposal is that you explore the entire codebase so you can understand which are the subsystems, pick one subsystem of your choice and a completely random subsystem, deep dive on both, and understand how they work. after that, explain me your approach, what you have learned and your perception about the system you're operating, with the extra note that you should not think as a random user - think as **claude** user. as consultant, developer, tool designer, my counterpart...

> can you carefully think what would be your approach to proceed with the same investigation only with native tools and infer how many tokens you'd have spent to get the same amount of information?

# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ## #
#################################################################################################
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ## #
# ## ### ## # ## # ## # ## ### ## # ## # ## # ## ### ## # ## # ## # ## ### ## # ## # ## # ## ###
# #  ##  #  # #  # #  # #  ##  #  # #  # #  # #  #   #  # #  # #  # #  ##  #  # #  # #  # #  ##
#  #   #  # #  # # #  #  #   # #  #  # #  # #  #   # #  #  # #  # # #   #   # #  # #  # #  #   #
#  #   #  # #  # # #  #  #   # #  #  # #  # #  #   # #  #  # #  # # #   #   # #  # #  # #  #   #
 ##     ##   ##   #    ##     #    ##   ##   ##     #    ##   ##   # ##   ##   ##   ##   ##   #
#      #    #    #    #      #    #    #    #      #    #    #    # #    #    #    #    #    ##
##     ##   ##        ##          ##   ##   ##          ##   ##     ##        ##   ##        #
 #       ###         #              ###    #              ###      #            ###           #

Check deadcode:
```python
from nabu.mcp.utils.workflow_helpers import (
    calculate_risk_score,
    calculate_centrality_score,
    calculate_core_score,
    generate_mermaid_graph,
    aggregate_affected_files,
    generate_change_recommendations,
    find_test_files_for_class
)
```