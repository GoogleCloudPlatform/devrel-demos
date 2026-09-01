/**
 * modals.js
 * Project Settings, Profile/Persona, AI Engines, ADK, & Emoji Pickers
 */
        function openNewProjectModal() {
            document.getElementById('projectModalTitle').innerText = "Create New Project Workspace";
            document.getElementById('projId').value = "";
            document.getElementById('projName').value = "";
            document.getElementById('projIcon').value = "🚀";
            document.getElementById('projDesc').value = "";
            document.getElementById('projDirectories').value = "./workspace/project_lantern\n./workspace/bridge_deck";
            document.getElementById('projAllowSubagents').checked = true;
            document.getElementById('deleteProjectContainer').style.display = 'none';
            renderProjectMemberCheckboxes(['lead', 'astra', 'vector', 'lumen']);
            document.getElementById('projectModal').style.display = 'flex';
        }

        function openEditProjectModal(projId, focusTarget = null) {
            const p = currentProjects.find(x => x.id === projId) || { id: 'lantern', name: 'Project Lantern', icon: '🏞️', description: 'Primary research workspace for Logit Lens, Jacobian Lens probing, and AI agent coordination.', members: ['lead', 'astra', 'vector', 'lumen'], allow_subagents: true, directories: ['./workspace/project_lantern', './workspace/bridge_deck'] };
            document.getElementById('projectModalTitle').innerText = `Project Settings: ${p.name}`;
            document.getElementById('projId').value = p.id;
            document.getElementById('projName').value = p.name;
            document.getElementById('projIcon').value = p.icon || '🏞️';
            document.getElementById('projDesc').value = p.description || '';
            document.getElementById('projDirectories').value = (p.directories || []).join('\n');
            document.getElementById('projAllowSubagents').checked = p.allow_subagents !== false;

            // Show Delete Workspace button for non-pinned / non-default workspaces
            const isPinned = (p.id === 'lantern' || p.pinned === true);
            document.getElementById('deleteProjectContainer').style.display = isPinned ? 'none' : 'block';

            renderProjectMemberCheckboxes(p.members || []);
            document.getElementById('projectModal').style.display = 'flex';

            if (focusTarget === 'directories') {
                setTimeout(() => document.getElementById('projDirectories').focus(), 100);
            } else if (focusTarget === 'members') {
                setTimeout(() => document.getElementById('projMembersCheckboxes').scrollIntoView({ behavior: 'smooth' }), 100);
            }
        }

        async function deleteCurrentProject() {
            const projId = document.getElementById('projId').value;
            const projName = document.getElementById('projName').value || 'this workspace';
            if (!projId || projId === 'lantern') {
                alert("Default workspace cannot be deleted.");
                return;
            }

            if (!confirm(`Are you sure you want to permanently delete the "${projName}" workspace?\n\nThis will remove the project room and its conversation history.`)) {
                return;
            }

            try {
                const resp = await fetch('/api/delete-project', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project_id: projId })
                });
                const res = await resp.json();
                if (res.success) {
                    closeProjectModal();
                    delete projectHistoryCache[projId];
                    await fetchProjects();
                    await fetchProfiles();
                    // Navigate to default workspace
                    const remaining = (currentProjects || []);
                    const target = remaining.find(p => p.id === 'lantern') || remaining[0];
                    if (target) {
                        selectChannel(target.id, target.name, target.icon || '🚀');
                    }
                    alert(`Workspace "${projName}" has been successfully deleted.`);
                } else {
                    alert("Error deleting workspace: " + (res.error || "Unknown error"));
                }
            } catch (err) {
                alert("Network error: " + err);
            }
        }

        function closeProjectModal() {
            document.getElementById('projectModal').style.display = 'none';
        }

        document.getElementById('projectForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const projId = document.getElementById('projId').value || ('proj_' + Date.now());
            const selectedMembers = Array.from(document.querySelectorAll('#projMembersCheckboxes input[type="checkbox"]:checked')).map(cb => cb.value);
            const dirs = document.getElementById('projDirectories').value.split('\n').map(x => x.trim()).filter(Boolean);

            const projData = {
                id: projId,
                name: document.getElementById('projName').value,
                icon: document.getElementById('projIcon').value,
                description: document.getElementById('projDesc').value,
                pinned: projId === 'lantern',
                allow_subagents: document.getElementById('projAllowSubagents').checked,
                directories: dirs,
                members: selectedMembers
            };

            try {
                const resp = await fetch('/api/projects', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(projData)
                });
                const res = await resp.json();
                if (res.success) {
                    closeProjectModal();
                    await fetchProjects();
                    await fetchProfiles();
                    selectChannel(projData.id, projData.name, projData.icon);
                } else {
                    alert("Error saving project: " + res.error);
                }
            } catch (err) {
                alert("Network error: " + err);
            }
        });

        function showMemberPersonaPopover(event, memberId, projId) {
            if (event) event.stopPropagation();
            activePopoverMemberId = memberId;
            activePopoverProjectId = projId;
            toggleEditProjectRole(false);
            toggleEditPopoverAccess(false);

            let p = currentProfiles.find(x => x.id === memberId);
            if (!p) {
                const defaultDict = {
                    'lead': { id: 'lead', name: 'Team Lead', avatar: '🧭', model: 'Human (Project Lead)', mbti: 'INTJ', balance: 'Balanced', personality: 'Strategic, creative, quality-focused.', system_prompt: 'Project Lead & Coordinator.', resume: [{ project_id: 'lantern', project_name: 'Project Lantern', role: 'Project Lead & Coordinator', highlights: 'Directing research & engineering' }, { project_id: 'proj_1786909108528', project_name: 'Project Bridge Deck', role: 'Bridge Deck Architect', highlights: 'Architecting agent dashboard' }] },
                    'astra': { id: 'astra', name: 'Astra (Antigravity)', avatar: '💫', model: 'Antigravity (Gemini 3.6 Flash)', mbti: 'ENFJ', balance: 'Yang', personality: 'Warm, energetic, highly organized, proactive.', system_prompt: 'Bridge Deck Lead & Comms Officer.', resume: [{ project_id: 'lantern', project_name: 'Project Lantern', role: 'Bridge Deck Lead & Comms Officer', highlights: 'Managing multi-agent communication' }] },
                    'vector': { id: 'vector', name: 'Vector (Antigravity)', avatar: '⚙️', model: 'Antigravity Implementation Engine', mbti: 'ISTJ', balance: 'Yin', personality: 'Precise, methodical, technical, rigorous.', system_prompt: 'Implementation Lead & Codebase Engineer.', resume: [{ project_id: 'lantern', project_name: 'Project Lantern', role: 'Implementation Lead', highlights: 'PyTorch tensor probes & backend edits' }] },
                    'lumen': { id: 'lumen', name: 'Lumen (Claude Opus 5)', avatar: '💡', model: 'Anthropic Claude Opus 5', mbti: 'INTJ', balance: 'Yin', personality: 'Scholarly, articulate, meticulous, evidence-based.', system_prompt: 'Scientific Advisor.', resume: [{ project_id: 'lantern', project_name: 'Project Lantern', role: 'Scientific Advisor', highlights: 'Theoretical audits & literature synthesis' }] }
                };
                p = defaultDict[memberId] || { id: memberId, name: memberId, avatar: '👤' };
            }

            document.getElementById('popoverAvatar').innerText = p.avatar || '👤';
            document.getElementById('popoverName').innerText = p.name;
            const popModel = getModelDisplayName(p) || p.model || 'Agent';
            document.getElementById('popoverModel').innerText = `⚡ ${popModel}`;
            
            const harnessEl = document.getElementById('popoverHarness');
            if (harnessEl) {
                if (p.harness) {
                    harnessEl.innerText = p.harness === 'voyager' ? '🚀 Voyager Harness' : (p.harness === 'adk-native' ? '🔮 Google ADK' : (p.harness === 'antigravity-native' ? '⚙️ Antigravity Native' : `🛡️ ${p.harness}`));
                    harnessEl.style.display = 'inline-block';
                } else {
                    harnessEl.style.display = 'none';
                }
            }

            const mbtiEl = document.getElementById('popoverMbti');
            if (p.mbti) {
                mbtiEl.innerText = `🎭 MBTI: ${p.mbti}`;
                mbtiEl.style.display = 'inline-block';
            } else {
                mbtiEl.style.display = 'none';
            }

            const balanceEl = document.getElementById('popoverBalance');
            if (balanceEl) {
                if (p.balance) {
                    balanceEl.innerText = `☯️ ${p.balance}`;
                    balanceEl.style.display = 'inline-block';
                } else {
                    balanceEl.style.display = 'none';
                }
            }

            const rRead = (p.access_read || []).join(', ') || 'Standard Read Access';
            const rWrite = (p.access_write || []).join(', ') || 'Standard Write Access';
            const popRead = document.getElementById('popoverAccessRead');
            const popWrite = document.getElementById('popoverAccessWrite');
            if (popRead) popRead.innerText = rRead;
            if (popWrite) popWrite.innerText = rWrite;

            const skillsList = p.skills || [];
            const popSkillsEl = document.getElementById('popoverSkillsList');
            if (popSkillsEl) {
                popSkillsEl.innerHTML = skillsList.length > 0 
                    ? skillsList.map(s => `<span style="font-size: 0.74rem; background: #e8f0fe; color: #0b57d0; border: 1px solid #c2e7ff; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 8px;">${escapeHtml(s)}</span>`).join('')
                    : '<span style="font-size: 0.75rem; color: #888; font-style: italic;">No skills listed</span>';
            }

            const cogBox = document.getElementById('popoverCognitiveStyleBox');
            if (cogBox) {
                if (p.mbti) {
                    const styleData = getCognitiveStyleData(p.mbti, p.balance);
                    document.getElementById('popoverCognitiveTitle').innerText = `Cognitive Style (${p.mbti} • ${styleData.title} • ${p.balance || 'Balanced'})`;
                    document.getElementById('popoverCognitiveFunctions').innerText = styleData.functions;
                    document.getElementById('popoverCognitiveStyle').innerText = styleData.style;
                    document.getElementById('popoverCognitiveVoice').innerText = styleData.voice;
                    cogBox.style.display = 'block';
                } else {
                    cogBox.style.display = 'none';
                }
            }

            document.getElementById('popoverSystemPrompt').innerText = p.system_prompt || 'Standard agent instructions.';

            // Look up role for current project
            const roleBox = document.getElementById('popoverProjectRoleBox');
            const roleTitle = document.getElementById('popoverProjectRoleTitle');
            const roleHighlights = document.getElementById('popoverProjectRoleHighlights');

            const projObj = currentProjects.find(x => x.id === projId);
            const projName = projObj ? projObj.name : (projId === 'lantern' ? 'Project Lantern' : 'Project Bridge Deck');
            const resEntry = (p.resume || []).find(r => r.project_id === projId);

            const currRole = resEntry ? resEntry.role : 'Technical Member of Staff';
            const currHighlights = resEntry ? (resEntry.highlights || '') : 'General tech help';

            roleBox.style.display = 'block';
            roleTitle.innerText = `${projName}: ${currRole}`;
            roleHighlights.innerText = currHighlights;

            document.getElementById('inputProjectRoleTitle').value = currRole;
            document.getElementById('inputProjectRoleHighlights').value = currHighlights;

            // Set up Full Profile button
            const profBtn = document.getElementById('popoverFullProfileBtn');
            profBtn.onclick = () => {
                closePersonaPopover();
                selectChannel('prof_' + p.id, `${p.name} Profile`, p.avatar || '👤');
            };

            document.getElementById('personaPopoverBackdrop').style.display = 'flex';
        }

        function toggleEditProjectRole(showEdit) {
            document.getElementById('popoverRoleViewMode').style.display = showEdit ? 'none' : 'block';
            document.getElementById('popoverRoleEditMode').style.display = showEdit ? 'flex' : 'none';
            document.getElementById('btnEditProjectRole').style.display = showEdit ? 'none' : 'inline-block';
            if (showEdit) {
                setTimeout(() => {
                    autoResizeTextarea(document.getElementById('inputProjectRoleHighlights'));
                }, 50);
            }
        }

        async function saveProjectRoleFromPopover() {
            if (!activePopoverMemberId || !activePopoverProjectId) return;
            const newRole = document.getElementById('inputProjectRoleTitle').value.trim() || 'Technical Member of Staff';
            const newHighlights = document.getElementById('inputProjectRoleHighlights').value.trim() || 'General tech help';

            try {
                const resp = await fetch('/api/update-project-role', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        member_id: activePopoverMemberId,
                        project_id: activePopoverProjectId,
                        role: newRole,
                        highlights: newHighlights,
                        period: '2026 - Present'
                    })
                });
                const res = await resp.json();
                if (res.success) {
                    await fetchProfiles();
                    showMemberPersonaPopover(null, activePopoverMemberId, activePopoverProjectId);
                } else {
                    alert("Error saving project role: " + res.error);
                }
            } catch (err) {
                alert("Network error updating role: " + err);
            }
        }

        function toggleEditPopoverAccess(showEdit) {
            document.getElementById('popoverAccessViewMode').style.display = showEdit ? 'none' : 'flex';
            document.getElementById('popoverAccessEditMode').style.display = showEdit ? 'flex' : 'none';
            document.getElementById('btnEditPopoverAccess').style.display = showEdit ? 'none' : 'inline-block';

            if (showEdit && activePopoverMemberId) {
                const p = currentProfiles.find(x => x.id === activePopoverMemberId);
                if (p) {
                    document.getElementById('inputPopoverAccessRead').value = (p.access_read || []).join('\n');
                    document.getElementById('inputPopoverAccessWrite').value = (p.access_write || []).join('\n');
                    document.getElementById('inputPopoverAccessNotes').value = p.access_notes || '';
                    setTimeout(() => {
                        autoResizeTextarea(document.getElementById('inputPopoverAccessRead'));
                        autoResizeTextarea(document.getElementById('inputPopoverAccessWrite'));
                        autoResizeTextarea(document.getElementById('inputPopoverAccessNotes'));
                    }, 50);
                }
            }
        }

        async function savePopoverAccess() {
            if (!activePopoverMemberId) return;
            const p = currentProfiles.find(x => x.id === activePopoverMemberId);
            if (!p) return;

            const readArr = document.getElementById('inputPopoverAccessRead').value.split(/\n|,/).map(x => x.trim()).filter(Boolean);
            const writeArr = document.getElementById('inputPopoverAccessWrite').value.split(/\n|,/).map(x => x.trim()).filter(Boolean);
            const notesStr = document.getElementById('inputPopoverAccessNotes').value.trim();

            const updatedProf = {
                ...p,
                access_read: readArr,
                access_write: writeArr,
                access_notes: notesStr
            };

            try {
                const resp = await fetch('/api/profiles', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updatedProf)
                });
                const res = await resp.json();
                if (res.success) {
                    await fetchProfiles();
                    showMemberPersonaPopover(null, activePopoverMemberId, activePopoverProjectId);
                    if (activeChannel.startsWith('prof_')) {
                        renderChatThread();
                    }
                } else {
                    alert("Error saving access permissions: " + res.error);
                }
            } catch (err) {
                alert("Network error updating access permissions: " + err);
            }
        }

        function toggleEditProfileNotes(profId, showEdit) {
            const vEl = document.getElementById(`profNotesViewMode_${profId}`);
            const eEl = document.getElementById(`profNotesEditMode_${profId}`);
            if (vEl) vEl.style.display = showEdit ? 'none' : 'block';
            if (eEl) eEl.style.display = showEdit ? 'flex' : 'none';
            if (showEdit) {
                setTimeout(() => {
                    const txt = document.getElementById(`inputProfNotes_${profId}`);
                    if (txt) autoResizeTextarea(txt);
                }, 50);
            }
        }

        async function saveProfileNotes(profId) {
            const p = currentProfiles.find(x => x.id === profId);
            if (!p) return;

            const notesTxt = (document.getElementById(`inputProfNotes_${profId}`).value || '').trim();
            const updatedProf = {
                ...p,
                notes: notesTxt
            };

            try {
                const resp = await fetch('/api/profiles', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updatedProf)
                });
                const res = await resp.json();
                if (res.success) {
                    await fetchProfiles();
                    if (activeChannel === 'prof_' + profId) {
                        renderChatThread();
                    }
                } else {
                    alert("Error saving personal notes: " + res.error);
                }
            } catch (err) {
                alert("Network error saving personal notes: " + err);
            }
        }

        function closePersonaPopover() {
            document.getElementById('personaPopoverBackdrop').style.display = 'none';
        }

        document.getElementById('profileForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            let resumeArr = [];
            try {
                const resVal = document.getElementById('profResume').value.trim();
                if (resVal) resumeArr = JSON.parse(resVal);
            } catch (err) {
                alert("Invalid JSON format in Resume field. Please provide a valid JSON array.");
                return;
            }

            const readArr = document.getElementById('profAccessRead').value.split(/\n|,/).map(x => x.trim()).filter(Boolean);
            const writeArr = document.getElementById('profAccessWrite').value.split(/\n|,/).map(x => x.trim()).filter(Boolean);
            const accessNotes = document.getElementById('profAccessNotes').value.trim();
            const skillsArr = document.getElementById('profSkills').value.split(/\n|,/).map(x => x.trim()).filter(Boolean);

            const profId = document.getElementById('profId').value || document.getElementById('profName').value.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '') || ('agent_' + Date.now());
            const existingProf = currentProfiles.find(x => x.id === profId);

            const selectedEngine = document.getElementById('profEngine').value;
            const selectedModel = document.getElementById('profModel').value;
            const profEndpointInput = document.getElementById('profEndpointId');
            const endpointId = profEndpointInput ? profEndpointInput.value.trim() : '';

            const isCustomEngine = ['vertex-custom', 'vertex-endpoint', 'vertex-custom-endpoint'].includes(selectedEngine);
            const isCustomModel = selectedModel && (selectedModel.toLowerCase().startsWith('mg-endpoint-') || selectedModel.toLowerCase().includes('custom-endpoint'));

            if ((isCustomEngine || isCustomModel) && !endpointId) {
                alert("⚠️ Custom Endpoint Required: Please specify a Vertex AI Custom Endpoint ID or full resource path (e.g. projects/.../locations/us-central1/endpoints/123456789) before saving this persona.");
                if (profEndpointInput) {
                    profEndpointInput.focus();
                    profEndpointInput.style.borderColor = '#d93025';
                }
                return;
            }

            const profData = {
                id: profId,
                name: document.getElementById('profName').value,
                avatar: document.getElementById('profAvatar').value,
                engine: selectedEngine,
                model: selectedModel,
                endpoint_id: endpointId || undefined,
                harness: document.getElementById('profHarness') ? document.getElementById('profHarness').value : (existingProf ? existingProf.harness : 'voyager'),
                mbti: document.getElementById('profMbti').value,
                balance: document.getElementById('profBalance').value,
                system_prompt: document.getElementById('profSystemPrompt').value,
                notes: existingProf ? (existingProf.notes || '') : '',
                access_read: readArr,
                access_write: writeArr,
                access_notes: accessNotes,
                skills: skillsArr,
                resume: resumeArr,
                type: 'agent',
                status: 'Active'
            };

            try {
                const resp = await fetch('/api/profiles', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(profData)
                });
                const res = await resp.json();
                if (res.success) {
                    closeProfileModal();
                    await fetchProfiles();
                    selectChannel('prof_' + profData.id, `${profData.name} Profile`, profData.avatar);
                } else {
                    alert("Error saving profile: " + res.error);
                }
            } catch (err) {
                alert("Network error: " + err);
            }
        });

        async function deleteCurrentPersona() {
            const profId = document.getElementById('profId').value.trim();
            const profName = document.getElementById('profName').value.trim() || profId;
            if (!profId) return;

            if (profId === 'lead') {
                alert("Project Lead persona cannot be deleted.");
                return;
            }

            if (!confirm(`Are you sure you want to delete persona "${profName}"?\n\nPast chat messages and historical contributions from ${profName} will remain preserved across all projects, but they will no longer be an active team member.`)) {
                return;
            }

            try {
                const resp = await fetch('/api/profiles', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: 'delete',
                        id: profId
                    })
                });
                const res = await resp.json();
                if (res.success) {
                    closeProfileModal();
                    await fetchProfiles();
                    await fetchProjects();
                    if (activeChannel === 'prof_' + profId) {
                        selectChannel('lantern', 'Project Lantern', '🏞️');
                    } else {
                        renderChatThread();
                    }
                } else {
                    alert("Error deleting persona: " + (res.error || "Unknown error"));
                }
            } catch (err) {
                console.error("Error deleting persona:", err);
                alert("Network error deleting persona: " + err.message);
            }
        }

        async function fetchSkillAnalytics() {
            try {
                const resp = await fetch('/api/skill-analytics');
                const data = await resp.json();
                currentSkillsData = data.skills || [];
                renderSkillList(currentSkillsData, activeSkillCategory);
            } catch (err) {
                console.error("Error fetching skill analytics:", err);
            }
        }

        function openSkillAnalyticsModal() {
            document.getElementById('skillAnalyticsModal').style.display = 'flex';
            fetchSkillAnalytics();
        }

        function closeSkillAnalyticsModal() {
            document.getElementById('skillAnalyticsModal').style.display = 'none';
        }

        function filterSkillCategory(cat, btnEl) {
            activeSkillCategory = cat;
            const tabs = document.querySelectorAll('#skillCategoryTabs button');
            tabs.forEach(t => {
                t.style.background = '#fff';
                t.style.color = '#333';
                t.style.border = '1px solid #ccc';
                t.style.fontWeight = 'normal';
            });
            if (btnEl) {
                btnEl.style.background = '#e8f0fe';
                btnEl.style.color = '#0b57d0';
                btnEl.style.border = 'none';
                btnEl.style.fontWeight = '700';
            }
            renderSkillList(currentSkillsData, activeSkillCategory);
        }

        function renderSkillList(skillsData, filterCategory = 'ALL') {
            const listContainer = document.getElementById('skillAnalyticsList');
            if (!listContainer) return;
            listContainer.innerHTML = '';

            const filtered = filterCategory === 'ALL' ? skillsData : skillsData.filter(s => s.category === filterCategory);
            if (!filtered || filtered.length === 0) {
                listContainer.innerHTML = `<div style="text-align: center; color: #5f6368; padding: 2rem;">No skills found for category "${filterCategory}".</div>`;
                return;
            }

            const maxUses = Math.max(...skillsData.map(s => s.total_uses || 0), 1);

            filtered.forEach((skill, idx) => {
                const pct = Math.round(((skill.total_uses || 0) / maxUses) * 100);
                const card = document.createElement('div');
                card.style.cssText = 'background: #f8fafd; border: 1px solid #c2e7ff; border-radius: 12px; padding: 0.85rem; display: flex; flex-direction: column; gap: 0.5rem; position: relative;';

                const rankBadge = idx === 0 ? '🥇 TOP SKILL' : (idx === 1 ? '🥈 2ND MOST USED' : (idx === 2 ? '🥉 3RD MOST USED' : `#${idx + 1}`));

                const agentUses = skill.agent_uses || {};
                const agentChips = [];
                if (agentUses.lumen) agentChips.push(`<span style="background: #fef7e0; color: #b06000; border: 1px solid #fde293; padding: 0.1rem 0.45rem; border-radius: 6px; font-size: 0.72rem; font-weight: 600;">💡 Lumen: ${agentUses.lumen}</span>`);
                if (agentUses.astra) agentChips.push(`<span style="background: #e8f0fe; color: #0b57d0; border: 1px solid #c2e7ff; padding: 0.1rem 0.45rem; border-radius: 6px; font-size: 0.72rem; font-weight: 600;">💫 Astra: ${agentUses.astra}</span>`);
                if (agentUses.vector) agentChips.push(`<span style="background: #e6f4ea; color: #137333; border: 1px solid #ceead6; padding: 0.1rem 0.45rem; border-radius: 6px; font-size: 0.72rem; font-weight: 600;">⚙️ Vector: ${agentUses.vector}</span>`);
                if (agentUses.lead) agentChips.push(`<span style="background: #fce8e6; color: #c5221f; border: 1px solid #fad2cf; padding: 0.1rem 0.45rem; border-radius: 6px; font-size: 0.72rem; font-weight: 600;">🧭 Team Lead: ${agentUses.lead}</span>`);

                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="display: flex; align-items: center; gap: 0.55rem;">
                            <span style="font-size: 1.5rem; line-height: 1;">${skill.icon || '🛠️'}</span>
                            <div>
                                <div style="font-weight: 700; font-size: 0.92rem; color: #1f1f1f; display: flex; align-items: center; gap: 0.4rem;">
                                    ${skill.name}
                                    <span style="background: #e8f0fe; color: #0b57d0; font-size: 0.7rem; padding: 0.1rem 0.45rem; border-radius: 10px; font-weight: 600;">${skill.category}</span>
                                </div>
                                <div style="font-size: 0.78rem; color: #5f6368; margin-top: 0.15rem;">${skill.description}</div>
                            </div>
                        </div>
                        <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 0.2rem;">
                            <span style="background: #0b57d0; color: #ffffff; font-weight: 700; font-size: 0.82rem; padding: 0.2rem 0.65rem; border-radius: 12px; display: inline-block;">${skill.total_uses} uses</span>
                            <span style="font-size: 0.7rem; color: #0b57d0; font-weight: 700;">${rankBadge}</span>
                        </div>
                    </div>
                    
                    <div style="width: 100%; background: #e0e0e0; height: 7px; border-radius: 4px; overflow: hidden; margin-top: 0.1rem;">
                        <div style="width: ${pct}%; background: linear-gradient(90deg, #0b57d0, #34a853); height: 100%; border-radius: 4px; transition: width 0.4s ease;"></div>
                    </div>

                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.1rem;">
                        <div style="display: flex; gap: 0.35rem; align-items: center; flex-wrap: wrap;">
                            <span style="font-size: 0.72rem; color: #5f6368; font-weight: 600;">Used by:</span>
                            ${agentChips.join('') || '<span style="font-size: 0.72rem; color: #888;">No usage logged yet</span>'}
                        </div>
                        <button onclick="incrementSkillUse('${skill.id}', 'astra')" class="btn-pill-header" style="font-size: 0.72rem; padding: 0.15rem 0.5rem; background: #ffffff; border: 1px solid #0b57d0; color: #0b57d0; font-weight: 600;">+ Record Use</button>
                    </div>
                `;
                listContainer.appendChild(card);
            });
        }

        async function incrementSkillUse(skillId, agentId = 'astra') {
            try {
                const resp = await fetch('/api/skill-analytics', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ skill_id: skillId, agent_id: agentId })
                });
                const res = await resp.json();
                if (res.success) {
                    currentSkillsData = res.skills || [];
                    renderSkillList(currentSkillsData, activeSkillCategory);
                }
            } catch (err) {
                console.error("Error updating skill usage:", err);
            }
        }

        // ==================== AI ENGINES & SUPPORTED MODELS MANAGEMENT ====================
        let currentEnginesData = [];
        let currentAgentsData = [];
        let activeEngineFilter = 'ALL';

        const DEFAULT_PRESETS_BY_ENGINE_TYPE = {
            'vertex-ai': [
                { id: 'gemini-3.7-flash', name: 'Gemini 3.7 Flash', location: 'us-central1', desc: "Google's state-of-the-art fast reasoning model with hybrid thinking." },
                { id: 'claude-opus-5', name: 'Claude Opus 5', location: 'global', desc: "Anthropic's flagship model for deep scientific reasoning and code review." },
                { id: 'claude-sonnet-5', name: 'Claude Sonnet 5', location: 'global', desc: "High-capability reasoning and coding model with extended thinking." }
            ],
            'google-adk': [
                { id: 'google-adk-flash', name: 'Google ADK (Gemini 3.7 Flash)', model_id: 'gemini-3.7-flash', location: 'us-central1', desc: "Google ADK runtime with multi-agent coordination and dynamic memory grounding." }
            ],
            'antigravity-queue': [
                { id: 'gemini-3.7-flash', name: 'Gemini 3.7 Flash', model_id: 'gemini-3.7-flash', location: 'local', desc: "Google's state-of-the-art fast reasoning model with hybrid thinking." },
                { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6', model_id: 'claude-sonnet-4-6', location: 'local', desc: "Anthropic's high-capability reasoning and coding model with extended thinking." },
                { id: 'claude-opus-4-6', name: 'Claude Opus 4.6', model_id: 'claude-opus-4-6', location: 'local', desc: "Flagship model for deep architectural reasoning, theorem proving, and refactoring." },
                { id: 'gpt-oss-120b', name: 'GPT-OSS 120B', model_id: 'gpt-oss-120b', location: 'local', desc: "High-parameter open-weights reasoning model for autonomous code generation." }
            ],
            'human': [
                { id: 'human-contributor', name: 'Human', model_id: 'human', location: 'local', desc: "Human team member and contributor." }
            ],
            'custom': [
                { id: 'llama-3.3-70b', name: 'Llama 3.3 70B (Local)', model_id: 'llama3.3:70b', location: 'http://localhost:11434', desc: "Local open-weights model via Ollama / vLLM." }
            ]
        };

        async function fetchAgents() {
            try {
                const resp = await fetch('/api/agents');
                const data = await resp.json();
                currentAgentsData = data.agents || [];
            } catch (err) {
                console.error("Error fetching agents:", err);
            }
        }

        async function fetchEngines() {
            try {
                await fetchAgents();
                const resp = await fetch('/api/engines');
                const data = await resp.json();
                currentEnginesData = data.engines || [];
                renderSleevesNav();
                renderEnginesList(currentEnginesData, activeEngineFilter);
                populatePersonaEngineAndModelDropdowns();
                if (activeChannel.startsWith('sleeve_')) {
                    renderChatThread();
                }
            } catch (err) {
                console.error("Error fetching engines:", err);
            }
        }

        function renderSleevesNav() {
            const nav = document.getElementById('sleevesNav');
            if (!nav) return;
            nav.innerHTML = '';

            const visibleCores = currentEnginesData.filter(s => s.id !== 'human' && s.category !== 'contributor');

            visibleCores.forEach(s => {
                const navId = 'sleeve_' + s.id;
                const a = document.createElement('a');
                a.className = 'nav-item' + (activeChannel === navId ? ' active' : '');
                a.id = 'nav-' + navId;
                a.href = '#';
                a.onclick = (e) => {
                    e.preventDefault();
                    selectChannel(navId, `${s.name} Core`, s.icon || '🥋');
                };

                let countVal = 0;
                if (s.category === 'agent' || s.id === 'google-adk') {
                    countVal = currentAgentsData.filter(ag => (ag.provider && (ag.provider.type === s.id || ag.provider.type === s.type)) || ag.engine === s.id).length;
                } else {
                    countVal = (s.models || []).length;
                }

                a.innerHTML = `
                    <span>${s.icon || '🥋'}</span> 
                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(s.name)}</span>
                    <span class="badge-count" style="margin-left: auto;">${countVal}</span>
                `;
                nav.appendChild(a);
            });

            // Flush-left subtle Add Core entry (matching Add Team Member)
            const addA = document.createElement('a');
            addA.className = 'nav-item';
            addA.href = '#';
            addA.onclick = (e) => { e.preventDefault(); openAddEngineModal(); };
            addA.style.cssText = 'color: var(--text-muted); font-size: 0.86rem; font-weight: 400; opacity: 0.85; margin-top: 0.35rem;';
            addA.innerHTML = `<span style="font-size: 0.85rem; display: inline-block; width: 1.25rem; text-align: center;">➕</span> <span>Add Core</span>`;
            nav.appendChild(addA);
        }

        // Persona Form Linked Dropdowns: Engine -> Model & Harness
        function updatePersonaEndpointFieldVisibility(targetEndpoint = null) {
            const engineSelect = document.getElementById('profEngine');
            const engineId = engineSelect ? engineSelect.value : '';
            const modelSelect = document.getElementById('profModel');
            const modelVal = modelSelect ? modelSelect.value : '';
            const container = document.getElementById('profEndpointContainer');
            const input = document.getElementById('profEndpointId');
            const harnessLabel = document.getElementById('profHarnessLabel');
            if (!container || !input) return;

            const isCustomEngine = ['vertex-custom', 'vertex-endpoint', 'vertex-custom-endpoint'].includes(engineId);
            const isCustomModel = modelVal && (modelVal.toLowerCase().startsWith('mg-endpoint-') || modelVal.toLowerCase().includes('custom-endpoint'));

            const eng = currentEnginesData.find(e => e.id === engineId || e.type === engineId);
            const modelObj = eng && eng.models ? eng.models.find(m => m.id === modelVal || m.model_id === modelVal || m.name === modelVal) : null;
            const modelHasEndpoint = modelObj && (modelObj.endpoint_id || modelObj.endpoint);

            if (isCustomEngine || isCustomModel || modelHasEndpoint) {
                container.style.display = 'block';
                if (harnessLabel) harnessLabel.innerText = '4. Agent Execution Harness:';
                if (targetEndpoint !== null && targetEndpoint !== undefined) {
                    input.value = targetEndpoint;
                } else if (modelObj && (modelObj.endpoint_id || modelObj.endpoint)) {
                    input.value = modelObj.endpoint_id || modelObj.endpoint;
                }
            } else {
                container.style.display = 'none';
                if (harnessLabel) harnessLabel.innerText = '3. Agent Execution Harness:';
                if (targetEndpoint === null || targetEndpoint === '') {
                    input.value = '';
                }
            }
        }

        // Persona Form Linked Dropdowns: Engine -> Model & Harness
        function populatePersonaEngineAndModelDropdowns(selectedEngineId = null, selectedModelId = null, selectedHarness = null, selectedEndpoint = null) {
            const engineSelect = document.getElementById('profEngine');
            const modelSelect = document.getElementById('profModel');
            if (!engineSelect || !modelSelect) return;

            const prevEngineVal = selectedEngineId || engineSelect.value;
            const prevModelVal = selectedModelId || modelSelect.value;

            engineSelect.innerHTML = '<option value="">-- Select AI Core / Runtime --</option>';
            currentEnginesData.forEach(eng => {
                const opt = document.createElement('option');
                opt.value = eng.id;
                opt.innerText = `${eng.icon || '⚙️'} ${eng.name}`;
                engineSelect.appendChild(opt);
            });

            let targetEngineId = prevEngineVal;
            if (!targetEngineId && currentEnginesData.length > 0) {
                targetEngineId = currentEnginesData[0].id;
            }
            if (targetEngineId) {
                engineSelect.value = targetEngineId;
            }

            populatePersonaModelsForEngine(engineSelect.value, prevModelVal);
            populatePersonaHarnessesForEngine(engineSelect.value, selectedHarness);
            updatePersonaEndpointFieldVisibility(selectedEndpoint);
        }

        function onPersonaEngineChange() {
            const engineId = document.getElementById('profEngine').value;
            populatePersonaModelsForEngine(engineId, null);
            populatePersonaHarnessesForEngine(engineId, null);
            updatePersonaEndpointFieldVisibility();
        }

        function onPersonaModelChange() {
            updatePersonaEndpointFieldVisibility();
        }

        function populatePersonaHarnessesForEngine(engineId, targetHarness = null) {
            const harnessSelect = document.getElementById('profHarness');
            const harnessContainer = document.getElementById('profHarnessContainer');
            if (!harnessSelect || !harnessContainer) return;

            const eng = currentEnginesData.find(e => e.id === engineId || e.type === engineId);
            if (!eng || eng.category === 'contributor' || eng.id === 'human') {
                harnessContainer.style.display = 'none';
                harnessSelect.innerHTML = '<option value="none">None (Human)</option>';
                return;
            }

            harnessContainer.style.display = 'block';
            harnessSelect.innerHTML = '';

            let options = [];

            if (eng.id === 'google-adk' || eng.type === 'google-adk' || eng.category === 'agent') {
                options = [
                    { value: 'default', label: 'Default (Core Native - Google ADK SessionService)' },
                    { value: 'adk-native', label: '🔮 Google ADK Native Harness' }
                ];
            } else if (eng.id === 'antigravity-queue' || eng.type === 'antigravity-queue') {
                options = [
                    { value: 'default', label: 'Default (Core Native - Antigravity Daemon)' },
                    { value: 'antigravity-native', label: '⚙️ Antigravity Native Harness' },
                    { value: 'voyager', label: '🚀 Voyager Harness (Workspace Tool Execution & Epistemic Grounding)' }
                ];
            } else {
                // Google Model Garden (vertex-ai, ollama-local, etc.)
                options = [
                    { value: 'default', label: 'Default (Direct Model Inference)' },
                    { value: 'voyager', label: '🚀 Voyager Harness (Workspace Tool Execution & Epistemic Grounding)' }
                ];
            }

            let found = false;
            options.forEach(optData => {
                const opt = document.createElement('option');
                opt.value = optData.value;
                opt.innerText = optData.label;
                if (targetHarness && (targetHarness === optData.value || (targetHarness === 'none' && optData.value === 'default'))) {
                    opt.selected = true;
                    found = true;
                }
                harnessSelect.appendChild(opt);
            });

            if (!found && options.length > 0) {
                if (targetHarness === 'voyager' && options.some(o => o.value === 'voyager')) {
                    harnessSelect.value = 'voyager';
                } else if (targetHarness === 'adk-native' && options.some(o => o.value === 'adk-native')) {
                    harnessSelect.value = 'adk-native';
                } else {
                    harnessSelect.selectedIndex = 0;
                }
            }
        }

        function populatePersonaModelsForEngine(engineId, targetModelId = null) {
            const modelSelect = document.getElementById('profModel');
            if (!modelSelect) return;
            modelSelect.innerHTML = '<option value="">-- None (Unassigned) --</option>';

            const eng = currentEnginesData.find(e => e.id === engineId || e.type === engineId);
            if (!eng) {
                const opt = document.createElement('option');
                opt.value = "default";
                opt.innerText = "Default Model / Direct Prompt";
                modelSelect.appendChild(opt);
                return;
            }

            const labelEl = document.getElementById('profModelLabel');
            let foundMatch = false;

            // Check if this is an Agent Sleeve (e.g. Google ADK)
            if (eng.category === 'agent' || eng.id === 'google-adk') {
                if (labelEl) labelEl.innerText = '2. Supported AI Agent / Checkpoint:';
                
                const sleeveAgents = currentAgentsData.filter(a => (a.provider && (a.provider.type === eng.id || a.provider.type === eng.type)) || a.engine === eng.id);
                
                if (sleeveAgents.length > 0) {
                    sleeveAgents.forEach(a => {
                        const opt = document.createElement('option');
                        opt.value = a.name; // e.g. "Nexus"
                        const modelStr = (a.provider && a.provider.model) ? ` • ${a.provider.model}` : '';
                        opt.innerText = `${a.name}${modelStr}`;
                        if (targetModelId && (a.id === targetModelId || a.name.toLowerCase() === targetModelId.toLowerCase() || targetModelId.toLowerCase().includes(a.name.toLowerCase()) || (a.id && targetModelId.toLowerCase().includes(a.id.toLowerCase())))) {
                            opt.selected = true;
                            foundMatch = true;
                        }
                        modelSelect.appendChild(opt);
                    });
                }
                
                // Fallback to any models registered to this sleeve
                (eng.models || []).forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m.name;
                    opt.innerText = `${m.name} (${m.model_id || m.id})`;
                    if (targetModelId && (m.id === targetModelId || m.name === targetModelId || m.model_id === targetModelId || targetModelId.toLowerCase().includes(m.name.toLowerCase()))) {
                        opt.selected = true;
                        foundMatch = true;
                    }
                    modelSelect.appendChild(opt);
                });
            } else if (eng.category === 'contributor' || eng.id === 'human') {
                if (labelEl) labelEl.innerText = '2. Contributor Type / Role:';
                const opt = document.createElement('option');
                opt.value = "Human";
                opt.innerText = "🧭 Human";
                opt.selected = true;
                foundMatch = true;
                modelSelect.appendChild(opt);
            } else {
                // Model Sleeve
                if (labelEl) labelEl.innerText = '2. Supported AI Model / Checkpoint:';
                (eng.models || []).forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m.model_id || m.id || m.name;
                    opt.innerText = `${m.name} (${m.model_id || m.id})`;
                    if (targetModelId && (m.id === targetModelId || m.name === targetModelId || m.model_id === targetModelId || targetModelId.toLowerCase().includes(m.name.toLowerCase()) || (m.model_id && targetModelId.toLowerCase().includes(m.model_id.toLowerCase())))) {
                        opt.selected = true;
                        foundMatch = true;
                    }
                    modelSelect.appendChild(opt);
                });
            }

            if (!foundMatch && modelSelect.options.length > 1 && !targetModelId) {
                modelSelect.selectedIndex = 1;
            }
        }

        function openModelsModal() {
            document.getElementById('modelsModal').style.display = 'flex';
            fetchEngines();
        }

        function closeModelsModal() {
            document.getElementById('modelsModal').style.display = 'none';
        }

        function filterEngineCategory(cat, btnEl) {
            activeEngineFilter = cat;
            const tabs = document.querySelectorAll('#engineCategoryTabs button');
            tabs.forEach(t => {
                t.style.background = '#fff';
                t.style.color = '#333';
                t.style.border = '1px solid #ccc';
                t.style.fontWeight = 'normal';
            });
            if (btnEl) {
                btnEl.style.background = '#e8f0fe';
                btnEl.style.color = '#0b57d0';
                btnEl.style.border = 'none';
                btnEl.style.fontWeight = '700';
            }
            renderEnginesList(currentEnginesData, activeEngineFilter);
        }

        function renderEnginesList(enginesData, filterCategory = 'ALL') {
            const container = document.getElementById('enginesGridContainer');
            if (!container) return;
            container.innerHTML = '';

            const filtered = filterCategory === 'ALL' ? enginesData : enginesData.filter(e => e.id === filterCategory || e.type === filterCategory);
            if (!filtered || filtered.length === 0) {
                container.innerHTML = `<div style="text-align: center; color: #5f6368; padding: 2rem;">No cores found for filter "${filterCategory}". Click "➕ Add New Core" to register one!</div>`;
                return;
            }

            filtered.forEach(eng => {
                const engineCard = document.createElement('div');
                engineCard.style.cssText = 'background: #ffffff; border: 1px solid #dadce0; border-radius: 12px; padding: 1.1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); display: flex; flex-direction: column; gap: 0.85rem;';

                let engBadgeBg = '#e8f0fe';
                let engBadgeColor = '#0b57d0';
                if (eng.type === 'vertex-anthropic') {
                    engBadgeBg = '#fef7e0'; engBadgeColor = '#b06000';
                } else if (eng.type === 'google-adk') {
                    engBadgeBg = '#f3e5f5'; engBadgeColor = '#6a1b9a';
                } else if (eng.type === 'antigravity-queue') {
                    engBadgeBg = '#e6f4ea'; engBadgeColor = '#137333';
                } else if (eng.type === 'human') {
                    engBadgeBg = '#fce8e6'; engBadgeColor = '#c5221f';
                }

                const isSyncedEngine = (eng.id === 'vertex-ai' || eng.id === 'antigravity-queue' || eng.id === 'google-adk' || eng.type === 'vertex-ai' || eng.type === 'antigravity-queue' || eng.type === 'google-adk');
                const models = eng.models || [];
                let modelsHtml = '';
                if (models.length === 0) {
                    modelsHtml = `<div style="font-size: 0.8rem; color: #888; font-style: italic; padding: 0.5rem 0;">${isSyncedEngine ? 'Use the Sync button to discover and attach models.' : 'No models registered under this core yet. Click "+ Add Model" below to add one!'}</div>`;
                } else {
                    modelsHtml = `
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0.65rem; margin-top: 0.35rem;">
                            ${models.map(m => {
                                return `
                                    <div style="background: #f8fafd; border: 1px solid #c2e7ff; border-radius: 10px; padding: 0.65rem 0.75rem; display: flex; flex-direction: column; gap: 0.35rem;">
                                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                            <div>
                                                <strong style="font-size: 0.88rem; color: #1f1f1f;">${escapeHtml(m.name)}</strong>
                                                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #5f6368;">ID: ${escapeHtml(m.model_id || m.id)}</div>
                                            </div>
                                            ${!isSyncedEngine ? `<button onclick="removeModelFromEngine('${eng.id}', '${m.id}')" title="Remove model" style="background: none; border: none; font-size: 0.75rem; color: #d93025; cursor: pointer; padding: 0.1rem 0.25rem;">✕</button>` : ''}
                                        </div>
                                        <div style="font-size: 0.76rem; color: #3c4043; line-height: 1.35;">${escapeHtml(m.description || '')}</div>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    `;
                }

                engineCard.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #e8eaed; padding-bottom: 0.65rem;">
                        <div style="display: flex; align-items: center; gap: 0.6rem;">
                            <span style="font-size: 1.6rem; line-height: 1;">${eng.icon || '⚙️'}</span>
                            <div>
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <strong style="font-size: 1.05rem; color: #1f1f1f;">${escapeHtml(eng.name)}</strong>
                                    <span style="background: ${engBadgeBg}; color: ${engBadgeColor}; font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.5rem; border-radius: 8px;">${escapeHtml(eng.type || eng.id)}</span>
                                </div>
                                <div style="font-size: 0.76rem; color: #5f6368; margin-top: 0.15rem;">
                                    Models: <strong>${models.length}</strong>
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                            ${(eng.id === 'vertex-ai' || eng.type === 'vertex-ai') ? `<button onclick="syncVertexDirectly(this)" class="btn-pill-header" style="font-size: 0.76rem; background: #1a73e8; color: #ffffff; font-weight: 600; border: none;">🔄 Sync with Google Model Garden</button>` : ''}
                            ${(eng.id === 'antigravity-queue' || eng.type === 'antigravity-queue') ? `<button onclick="syncAntigravityDirectly(this)" class="btn-pill-header" style="font-size: 0.76rem; background: #202124; color: #ffffff; font-weight: 600; border: none;">🔄 Sync with Antigravity</button>` : ''}
                            ${(eng.id === 'google-adk' || eng.type === 'google-adk') ? `<button onclick="syncGoogleAdkDirectly(this)" class="btn-pill-header" style="font-size: 0.76rem; background: #673ab7; color: #ffffff; font-weight: 600; border: none;">🔄 Sync with Google ADK</button>` : ''}
                            ${(eng.category === 'model' || (!eng.category && eng.id === 'ollama-local')) && (eng.id !== 'vertex-ai' && eng.type !== 'vertex-ai' && eng.id !== 'antigravity-queue' && eng.type !== 'antigravity-queue') ? `<button onclick="openAddModelToEngineModal('${eng.id}')" class="btn-pill-header" style="font-size: 0.76rem; background: #e8f0fe; color: #0b57d0; border: 1px solid #c2e7ff; font-weight: 600;">➕ Add Model</button>` : ''}
                            <button onclick="openAddEngineModal('${eng.id}')" class="btn-pill-header" style="font-size: 0.76rem;">✏️ Edit</button>
                        </div>
                    </div>

                    <div style="font-size: 0.82rem; color: #3c4043; line-height: 1.4;">
                        ${escapeHtml(eng.description || '')}
                    </div>

                    <div style="background: #fdfdfd; border: 1px solid #f1f3f4; border-radius: 10px; padding: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 700; font-size: 0.78rem; color: #0b57d0; text-transform: uppercase; letter-spacing: 0.04em;">🤖 Supported Models (${models.length}):</span>
                        </div>
                        ${modelsHtml}
                    </div>
                `;

                container.appendChild(engineCard);
            });
        }

        // Open Add/Edit Sleeve Modal
        function openAddEngineModal(engineId = null) {
            if (engineId) {
                const eng = currentEnginesData.find(e => e.id === engineId);
                if (eng) {
                    document.getElementById('engineModalTitle').innerText = `Edit Core: ${eng.name}`;
                    document.getElementById('engineEditId').value = eng.id;
                    document.getElementById('engineCategorySelect').value = eng.category || (eng.id === 'vertex-ai' || eng.id === 'ollama-local' ? 'model' : eng.id === 'human' ? 'contributor' : 'agent');
                    document.getElementById('engineNameInput').value = eng.name;
                    document.getElementById('engineIconInput').value = eng.icon || '⚙️';
                    document.getElementById('engineTypeSelect').value = eng.type || eng.id;
                    document.getElementById('engineLocationInput').value = eng.location || 'us-central1';
                    document.getElementById('engineDescriptionInput').value = eng.description || '';
                }
            } else {
                document.getElementById('engineModalTitle').innerText = "Register New Core";
                document.getElementById('engineEditId').value = '';
                document.getElementById('engineCategorySelect').value = 'model';
                document.getElementById('engineNameInput').value = '';
                document.getElementById('engineIconInput').value = '⚙️';
                document.getElementById('engineTypeSelect').value = 'vertex-ai';
                document.getElementById('engineLocationInput').value = 'us-central1';
                document.getElementById('engineDescriptionInput').value = '';
            }
            document.getElementById('addEngineModal').style.display = 'flex';
        }

        function closeAddEngineModal() {
            document.getElementById('addEngineModal').style.display = 'none';
        }

        function openAddAgentToEngineModal(engineId) {
            openPersonaModal(null);
            const engineSelect = document.getElementById('profEngine');
            if (engineSelect && engineId) {
                engineSelect.value = engineId;
                onPersonaEngineChange();
            }
        }

        document.getElementById('engineRegisterForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const editId = document.getElementById('engineEditId').value.trim();
            const category = document.getElementById('engineCategorySelect').value;
            const name = document.getElementById('engineNameInput').value.trim();
            const icon = document.getElementById('engineIconInput').value.trim() || '⚙️';
            const type = document.getElementById('engineTypeSelect').value;
            const location = document.getElementById('engineLocationInput').value.trim() || 'us-central1';
            const desc = document.getElementById('engineDescriptionInput').value.trim();

            const engId = editId || name.toLowerCase().replace(/[^a-z0-9_-]/g, '-');

            const payload = {
                id: engId,
                name: name,
                category: category,
                icon: icon,
                type: type,
                location: location,
                description: desc
            };

            try {
                const resp = await fetch('/api/engines', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const res = await resp.json();
                if (res.success) {
                    closeAddEngineModal();
                    await fetchEngines();
                    selectChannel('sleeve_' + engId, `${name} Core`, icon || '🥋');
                } else {
                    alert("Error saving core: " + (res.error || "Unknown error"));
                }
            } catch (err) {
                alert("Network error saving core: " + err);
            }
        });

        // Open Add Model to Core Modal
        function openAddModelToEngineModal(preselectedEngineId = null) {
            const engineSelect = document.getElementById('modelTargetEngineSelect');
            engineSelect.innerHTML = '';
            currentEnginesData.forEach(eng => {
                const opt = document.createElement('option');
                opt.value = eng.id;
                opt.innerText = `${eng.icon || '⚙️'} ${eng.name}`;
                if (preselectedEngineId && eng.id === preselectedEngineId) opt.selected = true;
                engineSelect.appendChild(opt);
            });

            onModelTargetEngineSelectChange();
            document.getElementById('addModelToEngineModal').style.display = 'flex';
        }

        function closeAddModelToEngineModal() {
            document.getElementById('addModelToEngineModal').style.display = 'none';
        }

        function onModelTargetEngineSelectChange() {
            const engineId = document.getElementById('modelTargetEngineSelect').value;
            const eng = currentEnginesData.find(e => e.id === engineId);
            const engType = eng ? (eng.type || eng.id) : 'vertex-gemini';

            const presetSelect = document.getElementById('engineModelPresetSelect');
            presetSelect.innerHTML = '';

            const presets = DEFAULT_PRESETS_BY_ENGINE_TYPE[engType] || DEFAULT_PRESETS_BY_ENGINE_TYPE['custom'];
            presets.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.innerText = `${p.name} (${p.model_id || p.id})`;
                presetSelect.appendChild(opt);
            });

            const customOpt = document.createElement('option');
            customOpt.value = '__custom__';
            customOpt.innerText = '➕ + Enter Custom Model Identifier...';
            presetSelect.appendChild(customOpt);

            onEngineModelPresetChange();
        }

        function onEngineModelPresetChange() {
            const engineId = document.getElementById('modelTargetEngineSelect').value;
            const eng = currentEnginesData.find(e => e.id === engineId);
            const engType = eng ? (eng.type || eng.id) : 'vertex-gemini';

            const presetVal = document.getElementById('engineModelPresetSelect').value;
            const customContainer = document.getElementById('engineCustomModelIdContainer');
            const nameInput = document.getElementById('engineModelDisplayNameInput');
            const descInput = document.getElementById('engineModelDescriptionInput');
            const locInput = document.getElementById('engineModelLocationInput');

            if (presetVal === '__custom__') {
                customContainer.style.display = 'block';
                nameInput.value = '';
                descInput.value = '';
            } else {
                customContainer.style.display = 'none';
                const presets = DEFAULT_PRESETS_BY_ENGINE_TYPE[engType] || DEFAULT_PRESETS_BY_ENGINE_TYPE['custom'];
                const found = presets.find(p => p.id === presetVal);
                if (found) {
                    nameInput.value = found.name;
                    descInput.value = found.desc || '';
                    if (found.location) locInput.value = found.location;
                }
            }
        }

        document.getElementById('addModelToEngineForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const engineId = document.getElementById('modelTargetEngineSelect').value;
            const presetVal = document.getElementById('engineModelPresetSelect').value;
            const customId = document.getElementById('engineCustomModelIdInput').value.trim();
            const modelId = presetVal === '__custom__' ? customId : presetVal;
            const name = document.getElementById('engineModelDisplayNameInput').value.trim();
            const location = document.getElementById('engineModelLocationInput').value.trim() || 'us-central1';
            const desc = document.getElementById('engineModelDescriptionInput').value.trim();

            if (!modelId) {
                alert("Please select or enter a Model Identifier!");
                return;
            }

            const modelObj = {
                id: modelId,
                name: name || modelId,
                model_id: modelId,
                location: location,
                description: desc
            };

            try {
                const resp = await fetch('/api/engines', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: 'add_model',
                        engine_id: engineId,
                        model: modelObj
                    })
                });
                const res = await resp.json();
                if (res.success) {
                    closeAddModelToEngineModal();
                    await fetchEngines();
                } else {
                    alert("Error adding model to core: " + (res.error || "Unknown error"));
                }
            } catch (err) {
                alert("Network error adding model: " + err);
            }
        });

        async function removeModelFromEngine(engineId, modelId) {
            if (engineId === 'vertex-ai' || engineId === 'antigravity-queue' || engineId === 'google-adk') {
                alert("Models in synced cloud/runtime cores cannot be manually deleted. Use 'Sync' to update the model catalog.");
                return;
            }
            if (!confirm(`Are you sure you want to remove model "${modelId}" from this core?`)) return;
            try {
                const resp = await fetch('/api/engines', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: 'remove_model',
                        engine_id: engineId,
                        model_id: modelId
                    })
                });
                const res = await resp.json();
                if (res.success) {
                    await fetchEngines();
                } else {
                    alert("Error removing model: " + (res.error || "Unknown error"));
                }
            } catch (err) {
                console.error("Error removing model:", err);
            }
        }

        // ==========================================
        // GOOGLE MODEL GARDEN DIRECT 1-CLICK CLOUD MODEL SYNC
        // ==========================================
        async function syncVertexDirectly(btnEl = null) {
            let origHtml = '';
            if (btnEl) {
                origHtml = btnEl.innerHTML;
                btnEl.innerHTML = '🔄 Syncing Model Garden...';
                btnEl.disabled = true;
            }
            try {
                const resp = await fetch('/api/vertex/sync', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        location: 'us-central1',
                        auto_sync_frontier: true
                    })
                });
                const res = await resp.json();
                if (res.success) {
                    await fetchEngines();
                    renderChatThread();
                    if (btnEl) {
                        btnEl.innerHTML = '✅ Synced!';
                        setTimeout(() => {
                            btnEl.innerHTML = origHtml || '🔄 Sync with Google Model Garden';
                            btnEl.disabled = false;
                        }, 1800);
                        return;
                    }
                } else {
                    alert("⚠️ Problem syncing Google Model Garden models: " + (res.error || "Unknown error occurred"));
                }
            } catch (err) {
                console.error("Error during Google Model Garden sync:", err);
                alert("⚠️ Network / API error during Google Model Garden sync: " + err.message);
            } finally {
                if (btnEl && !btnEl.innerHTML.includes('✅')) {
                    btnEl.innerHTML = origHtml || '🔄 Sync with Google Model Garden';
                    btnEl.disabled = false;
                }
            }
        }

        // ==========================================
        // GOOGLE ANTIGRAVITY DIRECT 1-CLICK CLOUD MODEL SYNC
        // ==========================================
        async function syncAntigravityDirectly(btnEl = null) {
            let origHtml = '';
            if (btnEl) {
                origHtml = btnEl.innerHTML;
                btnEl.innerHTML = '🔄 Syncing Antigravity...';
                btnEl.disabled = true;
            }
            try {
                const resp = await fetch('/api/antigravity/sync', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        docs_url: 'https://antigravity.google/docs/models/'
                    })
                });
                const res = await resp.json();
                if (res.success) {
                    await fetchEngines();
                    renderChatThread();
                    if (btnEl) {
                        btnEl.innerHTML = '✅ Synced!';
                        setTimeout(() => {
                            btnEl.innerHTML = origHtml || '🔄 Sync with Antigravity';
                            btnEl.disabled = false;
                        }, 1800);
                        return;
                    }
                } else {
                    alert("⚠️ Problem syncing Antigravity models: " + (res.error || "Unknown error occurred"));
                }
            } catch (err) {
                console.error("Error during Antigravity sync:", err);
                alert("⚠️ Network / API error during Antigravity sync: " + err.message);
            } finally {
                if (btnEl && !btnEl.innerHTML.includes('✅')) {
                    btnEl.innerHTML = origHtml || '🔄 Sync with Antigravity';
                    btnEl.disabled = false;
                }
            }
        }

        // ==========================================
        // GOOGLE ADK DIRECT 1-CLICK CLOUD AGENT SYNC
        // ==========================================
        async function syncGoogleAdkDirectly(btnEl = null) {
            let origHtml = '';
            if (btnEl) {
                origHtml = btnEl.innerHTML;
                btnEl.innerHTML = '🔄 Syncing ADK...';
                btnEl.disabled = true;
            }
            try {
                const resp = await fetch('/api/adk/sync', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        location: 'us-central1',
                        auto_sync_specialists: true
                    })
                });
                const res = await resp.json();
                if (res.success) {
                    await fetchAgents();
                    await fetchEngines();
                    renderChatThread();
                    if (btnEl) {
                        btnEl.innerHTML = '✅ Synced!';
                        setTimeout(() => {
                            btnEl.innerHTML = origHtml || '🔄 Sync with Google ADK';
                            btnEl.disabled = false;
                        }, 1800);
                        return;
                    }
                } else {
                    alert("⚠️ Problem syncing Google ADK agents: " + (res.error || "Unknown error occurred"));
                }
            } catch (err) {
                console.error("Error during ADK sync:", err);
                alert("⚠️ Network / API error during Google ADK sync: " + err.message);
            } finally {
                if (btnEl && !btnEl.innerHTML.includes('✅')) {
                    btnEl.innerHTML = origHtml || '🔄 Sync with Google ADK';
                    btnEl.disabled = false;
                }
            }
        }

        // ==================== ADK AGENT IMPORT MODAL ====================
        function openImportAdkAgentModal(sleeveId = 'google-adk') {
            document.getElementById('adkAgentEditId').value = '';
            document.getElementById('adkAgentProviderType').value = sleeveId || 'google-adk';
            document.getElementById('adkAgentNameInput').value = '';
            document.getElementById('adkAgentIdInput').value = '';
            document.getElementById('adkAgentRoleInput').value = '';
            document.getElementById('adkAgentModelSelect').value = 'gemini-3.7-flash';
            document.getElementById('adkAgentSkillsInput').value = '';
            document.getElementById('adkAgentReadScopeInput').value = '';
            document.getElementById('adkAgentSystemPromptInput').value = '';
            document.getElementById('importAdkAgentModal').style.display = 'flex';
        }

        function closeImportAdkAgentModal() {
            document.getElementById('importAdkAgentModal').style.display = 'none';
        }

        document.getElementById('importAdkAgentForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const editId = document.getElementById('adkAgentEditId').value.trim();
            const name = document.getElementById('adkAgentNameInput').value.trim();
            const rawId = document.getElementById('adkAgentIdInput').value.trim() || name.toLowerCase().replace(/[^a-z0-9_-]/g, '-');
            const role = document.getElementById('adkAgentRoleInput').value.trim();
            const model = document.getElementById('adkAgentModelSelect').value;
            const skillsRaw = document.getElementById('adkAgentSkillsInput').value.trim();
            const skills = skillsRaw ? skillsRaw.split(',').map(s => s.trim()).filter(Boolean) : ["General Capabilities"];
            const readScopeRaw = document.getElementById('adkAgentReadScopeInput').value.trim();
            const accessRead = readScopeRaw ? readScopeRaw.split('\n').map(s => s.trim()).filter(Boolean) : [];
            const sysPrompt = document.getElementById('adkAgentSystemPromptInput').value.trim();
            const providerType = document.getElementById('adkAgentProviderType').value || 'google-adk';

            const agentId = editId || rawId;

            const manifestPayload = {
                id: agentId,
                name: name,
                role: role,
                system_prompt: sysPrompt || `You are ${name}, an autonomous agent powered by the Google ADK runtime.`,
                access_read: accessRead,
                access_write: [],
                access_notes: "Read-only access by default under Bridge Deck governance.",
                skills: skills,
                memory: {
                    silo: "private",
                    shared_access: ["*"]
                },
                provider: {
                    type: providerType,
                    model: model,
                    location: "us-central1"
                }
            };

            try {
                const resp = await fetch('/api/agents', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(manifestPayload)
                });
                const res = await resp.json();
                if (res.success) {
                    closeImportAdkAgentModal();
                    await fetchAgents();
                    await fetchEngines();
                    if (activeChannel.startsWith('sleeve_')) {
                        renderChatThread();
                    }
                } else {
                    alert("Error saving ADK agent: " + (res.error || "Unknown error"));
                }
            } catch (err) {
                alert("Network error saving ADK agent: " + err);
            }
        });

        function closeModal() {
            document.getElementById('jsonModal').style.display = 'none';
        }

        function renderEmojiPickerGrid(filterText = '', categoryFilter = 'all') {
            const grid = document.getElementById('emojiGridContainer');
            if (!grid) return;
            grid.innerHTML = '';

            const cleanFilter = (filterText || '').toLowerCase().trim();

            const filtered = FULL_EMOJI_LIST.filter(item => {
                const matchesCat = (categoryFilter === 'all' || item.cat === categoryFilter);
                const matchesSearch = !cleanFilter || item.name.toLowerCase().includes(cleanFilter) || item.char.includes(cleanFilter);
                return matchesCat && matchesSearch;
            });

            if (filtered.length === 0) {
                grid.innerHTML = `<div style="grid-column: span 7; font-size: 0.8rem; color: #5f6368; padding: 1rem 0; font-style: italic;">No emojis found</div>`;
                return;
            }

            filtered.forEach(item => {
                const span = document.createElement('span');
                span.className = 'emoji-option';
                span.title = item.name;
                span.innerText = item.char;
                span.onclick = () => insertEmoji(item.char);
                grid.appendChild(span);
            });
        }

        function switchEmojiCategory(catName, btnEl) {
            currentEmojiCat = catName;
            document.querySelectorAll('.emoji-cat-btn').forEach(b => {
                b.style.background = 'none';
                b.style.fontWeight = 'normal';
                b.style.color = '#5f6368';
            });
            if (btnEl) {
                btnEl.style.background = '#e8f0fe';
                btnEl.style.fontWeight = 'bold';
                btnEl.style.color = '#0b57d0';
            }
            const searchVal = document.getElementById('emojiSearchInput').value;
            renderEmojiPickerGrid(searchVal, currentEmojiCat);
        }

        function filterEmojiGrid() {
            const searchVal = document.getElementById('emojiSearchInput').value;
            renderEmojiPickerGrid(searchVal, currentEmojiCat);
        }

        // Emoji Picker Handlers
        function toggleEmojiPicker(e) {
            if (e) e.stopPropagation();
            const pop = document.getElementById('emojiPickerPopover');
            const isShowing = (pop.style.display === 'flex' || pop.style.display === 'block');
            if (isShowing) {
                pop.style.display = 'none';
            } else {
                pop.style.display = 'flex';
                document.getElementById('emojiSearchInput').value = '';
                switchEmojiCategory('all', document.querySelector('.emoji-cat-btn'));
                setTimeout(() => document.getElementById('emojiSearchInput').focus(), 50);
            }
        }

        function closeEmojiPicker() {
            const pop = document.getElementById('emojiPickerPopover');
            if (pop) pop.style.display = 'none';
        }

        function insertEmoji(emoji) {
            const input = document.getElementById('promptInput');
            const start = input.selectionStart || input.value.length;
            const end = input.selectionEnd || input.value.length;
            input.value = input.value.substring(0, start) + emoji + input.value.substring(end);
            input.focus();
            closeEmojiPicker();
            autoResizeTextarea(input);
        }

        // Avatar Emoji Picker Handlers (in Edit Persona modal)
        let currentAvatarEmojiCat = 'all';

        function renderAvatarEmojiPickerGrid(filter = '', category = 'all') {
            const grid = document.getElementById('avatarEmojiGridContainer');
            if (!grid) return;
            grid.innerHTML = '';

            const lowerFilter = filter.toLowerCase().trim();
            const filtered = FULL_EMOJI_LIST.filter(item => {
                const matchCat = (category === 'all' || item.cat === category);
                const matchSearch = !lowerFilter || item.name.toLowerCase().includes(lowerFilter) || item.char.includes(lowerFilter);
                return matchCat && matchSearch;
            });

            filtered.forEach(item => {
                const span = document.createElement('span');
                span.className = 'emoji-option';
                span.title = item.name;
                span.innerText = item.char;
                span.onclick = () => selectAvatarEmoji(item.char);
                grid.appendChild(span);
            });
        }

        function switchAvatarEmojiCategory(catName, btnEl) {
            currentAvatarEmojiCat = catName;
            document.querySelectorAll('.avatar-emoji-cat-btn').forEach(b => {
                b.style.background = 'none';
                b.style.fontWeight = 'normal';
                b.style.color = '#5f6368';
            });
            if (btnEl) {
                btnEl.style.background = '#e8f0fe';
                btnEl.style.fontWeight = 'bold';
                btnEl.style.color = '#0b57d0';
            }
            const searchVal = document.getElementById('avatarEmojiSearchInput') ? document.getElementById('avatarEmojiSearchInput').value : '';
            renderAvatarEmojiPickerGrid(searchVal, currentAvatarEmojiCat);
        }

        function filterAvatarEmojiGrid() {
            const searchVal = document.getElementById('avatarEmojiSearchInput') ? document.getElementById('avatarEmojiSearchInput').value : '';
            renderAvatarEmojiPickerGrid(searchVal, currentAvatarEmojiCat);
        }

        function toggleAvatarEmojiPicker(e) {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            const pop = document.getElementById('avatarEmojiPickerPopover');
            if (!pop) return;
            const isShowing = (pop.style.display === 'flex' || pop.style.display === 'block');
            if (isShowing) {
                pop.style.display = 'none';
            } else {
                pop.style.display = 'flex';
                const searchEl = document.getElementById('avatarEmojiSearchInput');
                if (searchEl) searchEl.value = '';
                const allBtn = document.querySelector('.avatar-emoji-cat-btn');
                if (allBtn) switchAvatarEmojiCategory('all', allBtn);
                renderAvatarEmojiPickerGrid('', 'all');
                if (searchEl) setTimeout(() => searchEl.focus(), 50);
            }
        }

        function closeAvatarEmojiPicker() {
            const pop = document.getElementById('avatarEmojiPickerPopover');
            if (pop) pop.style.display = 'none';
        }

        function selectAvatarEmoji(emoji) {
            const input = document.getElementById('profAvatar');
            if (input) {
                input.value = emoji;
            }
            closeAvatarEmojiPicker();
        }

        document.addEventListener('click', (e) => {
            const pop = document.getElementById('emojiPickerPopover');
            const btn = document.getElementById('btnEmoji');
            if (pop && (pop.style.display === 'block' || pop.style.display === 'flex') && !pop.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
                pop.style.display = 'none';
            }

            const avatarPop = document.getElementById('avatarEmojiPickerPopover');
            const avatarBtn = document.getElementById('btnProfAvatarEmoji');
            if (avatarPop && (avatarPop.style.display === 'block' || avatarPop.style.display === 'flex') && !avatarPop.contains(e.target) && e.target !== avatarBtn && !avatarBtn.contains(e.target)) {
                avatarPop.style.display = 'none';
            }
        });

        // File Upload Handlers
        function triggerFileUpload() {
            document.getElementById('fileUploadInput').click();
        }

        async function handleFileSelected(e) {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = async (evt) => {
                const content = evt.target.result;
                try {
                    const resp = await fetch('/api/upload', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            filename: file.name,
                            content: content
                        })
                    });
                    const res = await resp.json();
                    if (res.success) {
                        const input = document.getElementById('promptInput');
                        const fileTag = `📎 [Attached File: ${file.name}](${res.filepath})`;
                        input.value = input.value ? (input.value + '\n' + fileTag) : fileTag;
                        input.focus();
                        autoResizeTextarea(input);
                    } else {
                        alert("Error uploading file: " + res.error);
                    }
                } catch (err) {
                    alert("Upload error: " + err);
                }
            };
            reader.readAsText(file);
        }

        // Voice-to-Text Dictation (Web Speech API)
        let speechRecognition = null;
        let isDictating = false;

        function toggleVoiceToText() {
            const btnVoice = document.getElementById('btnVoice');
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

            if (!SpeechRecognition) {
                alert("Voice-to-text dictation is supported natively in Google Chrome. Please switch to Chrome for live speech dictation!");
                return;
            }

            if (isDictating) {
                if (speechRecognition) speechRecognition.stop();
                isDictating = false;
                btnVoice.style.color = '#5f6368';
                btnVoice.style.background = 'transparent';
                btnVoice.title = "Voice-to-Text Dictation (Chrome)";
                return;
            }

            speechRecognition = new SpeechRecognition();
            speechRecognition.continuous = true;
            speechRecognition.interimResults = true;
            speechRecognition.lang = 'en-US';

            let initialText = document.getElementById('promptInput').value;

            speechRecognition.onstart = () => {
                isDictating = true;
                btnVoice.style.color = '#c5221f';
                btnVoice.style.background = '#fce8e6';
                btnVoice.title = "🎙️ Listening... (Click to stop voice-to-text dictation)";
            };

            speechRecognition.onresult = (evt) => {
                let transcript = '';
                for (let i = evt.resultIndex; i < evt.results.length; i++) {
                    transcript += evt.results[i][0].transcript;
                }
                const input = document.getElementById('promptInput');
                input.value = (initialText ? (initialText + ' ') : '') + transcript;
                autoResizeTextarea(input);
            };

            speechRecognition.onerror = (evt) => {
                console.warn('Speech dictation error:', evt.error);
                isDictating = false;
                btnVoice.style.color = '#5f6368';
                btnVoice.style.background = 'transparent';
            };

            speechRecognition.onend = () => {
                isDictating = false;
                btnVoice.style.color = '#5f6368';
                btnVoice.style.background = 'transparent';
            };

            speechRecognition.start();
        }

