/**
 * chat.js
 * Chat Thread View, Message Dispatch, Autocomplete, & Attachments
 */
        function renderChatThread() {
            const threadEl = document.getElementById('chatThread');
            threadEl.innerHTML = '';
            if (activeChannel.startsWith('prof_') || activeChannel.startsWith('sleeve_')) {
                threadEl.scrollTop = 0;
            }

            if (activeChannel.startsWith('prof_')) {
                const pId = activeChannel.replace('prof_', '');
                const p = currentProfiles.find(x => x.id === pId);
                if (p) {
                    const profCard = document.createElement('div');
                    profCard.style.cssText = "background: #f8fafd; border: 1px solid #e1e3e1; border-radius: 18px; padding: 1.5rem; margin-bottom: 1.5rem;";
                    profCard.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                            <div style="display: flex; gap: 1rem; align-items: center;">
                                <div style="width: 56px; height: 56px; border-radius: 50%; background: #ffffff; display: flex; align-items: center; justify-content: center; font-size: 2rem; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                                    ${p.avatar || '👤'}
                                </div>
                                <div>
                                    <h2 style="font-size: 1.3rem; font-weight: 700;">${escapeHtml(p.name)}</h2>
                                    <div style="font-size: 0.78rem; color: #1b5e20; background: #e8f5e9; border: 1px solid #c8e6c9; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 10px; display: inline-block; margin-top: 0.3rem;">
                                        ${(p.id === 'lead' || p.engine === 'human') ? '🧭' : '⚡'} Cognition: ${escapeHtml(getModelDisplayName(p) || p.model || 'Agent Engine')}
                                    </div>
                                    ${(() => {
                                        const engObj = currentEnginesData.find(e => e.id === p.engine || e.type === p.engine);
                                        const sleeveName = engObj ? engObj.name : (p.engine === 'google-adk' ? 'Google ADK' : p.engine);
                                        const sleeveIcon = engObj ? (engObj.icon || '🔮') : '🔮';
                                        return sleeveName ? `<div style="font-size: 0.78rem; color: #0b57d0; background: #e8f0fe; border: 1px solid #c2e7ff; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 10px; display: inline-block; margin-top: 0.3rem; margin-left: 0.4rem;">${sleeveIcon} Core: ${escapeHtml(sleeveName)}</div>` : '';
                                    })()}
                                    ${p.harness ? `<div style="font-size: 0.78rem; color: #b06000; background: #fff8e1; border: 1px solid #ffe082; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 10px; display: inline-block; margin-top: 0.3rem; margin-left: 0.4rem; vertical-align: middle;">${p.harness === 'voyager' ? '🚀 Harness: Voyager' : (p.harness === 'adk-native' ? '🔮 Harness: Google ADK' : (p.harness === 'antigravity-native' ? '⚙️ Harness: Antigravity Native' : `🛡️ Harness: ${escapeHtml(p.harness)}`))}</div>` : ''}
                                    ${p.mbti ? `<div style="font-size: 0.78rem; color: #4a148c; background: #f3e5f5; border: 1px solid #e1bee7; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 10px; display: inline-block; margin-top: 0.3rem; margin-left: 0.4rem; vertical-align: middle;">🎭 MBTI: ${escapeHtml(p.mbti)}</div>` : ''}
                                    ${p.balance ? `<div style="font-size: 0.78rem; color: #0d47a1; background: #e3f2fd; border: 1px solid #bbdefb; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 10px; display: inline-block; margin-top: 0.3rem; margin-left: 0.4rem; vertical-align: middle;">☯️ ${escapeHtml(p.balance)}</div>` : ''}
                                </div>
                            </div>
                        </div>

                        <div style="display: flex; flex-direction: column; gap: 0.85rem; margin-top: 1.25rem;">
                            <div>
                                <strong style="font-size: 0.78rem; color: #5f6368; text-transform: uppercase; letter-spacing: 0.04em;">Who I am:</strong>
                                <div style="background: #1e1e1e; color: #4ec9b0; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; padding: 0.85rem; border-radius: 10px; margin-top: 0.35rem; white-space: pre-wrap; line-height: 1.5;">${escapeHtml(p.system_prompt || '')}</div>
                            </div>
                            ${(() => {
                                if (!p.mbti) return '';
                                const styleData = getCognitiveStyleData(p.mbti, p.balance);
                                return `
                                <div style="background: #fdf7ff; border: 1px solid #e1bee7; border-radius: 12px; padding: 0.85rem 1rem;">
                                    <div style="font-size: 0.8rem; font-weight: 700; color: #6a1b9a; margin-bottom: 0.45rem; display: flex; align-items: center; gap: 0.4rem;">
                                        <span>🎭</span> <span>COGNITIVE STYLE & WORKING DYNAMICS (${escapeHtml(p.mbti)} • ${escapeHtml(styleData.title)} • ${escapeHtml(p.balance || 'Balanced')})</span>
                                    </div>
                                    <div style="font-size: 0.82rem; color: #374151; line-height: 1.55; display: flex; flex-direction: column; gap: 0.35rem;">
                                        <div><strong>🧠 Cognitive Stack:</strong> ${escapeHtml(styleData.functions)}</div>
                                        <div><strong>⚡ Problem-Solving:</strong> ${escapeHtml(styleData.style)}</div>
                                        <div><strong>💬 Communication Voice:</strong> ${escapeHtml(styleData.voice)}</div>
                                        <div><strong>☯️ Energy Dynamic:</strong> ${escapeHtml(styleData.energy)}</div>
                                    </div>
                                </div>
                                `;
                            })()}
                            <div>
                                <strong style="font-size: 0.78rem; color: #5f6368; text-transform: uppercase; letter-spacing: 0.04em; display: block; margin-bottom: 0.4rem;">🔑 Read & Write Access Permissions:</strong>
                                <div style="background: #ffffff; border: 1px solid #e1e3e1; border-radius: 14px; padding: 1rem;">
                                    <div style="display: flex; gap: 0.85rem; flex-wrap: wrap;">
                                        <div style="flex: 1; min-width: 220px; background: #e8f0fe; border: 1px solid #c2e7ff; border-radius: 10px; padding: 0.75rem;">
                                            <div style="font-size: 0.8rem; font-weight: 700; color: #0b57d0; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.35rem;">
                                                <span>👁️</span> <span>READ ACCESS</span>
                                            </div>
                                            <div style="display: flex; flex-wrap: wrap; gap: 0.35rem;">
                                                ${(p.access_read && p.access_read.length > 0) ? p.access_read.map(r => `<span style="font-size: 0.78rem; background: #ffffff; color: #0b57d0; border: 1px solid #a8c7fa; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 8px;">${escapeHtml(r)}</span>`).join('') : '<span style="font-size: 0.78rem; color: #5f6368; font-style: italic;">No read paths configured</span>'}
                                            </div>
                                        </div>
                                        <div style="flex: 1; min-width: 220px; background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 10px; padding: 0.75rem;">
                                            <div style="font-size: 0.8rem; font-weight: 700; color: #1b5e20; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.35rem;">
                                                <span>✍️</span> <span>WRITE ACCESS</span>
                                            </div>
                                            <div style="display: flex; flex-wrap: wrap; gap: 0.35rem;">
                                                ${(p.access_write && p.access_write.length > 0) ? p.access_write.map(w => `<span style="font-size: 0.78rem; background: #ffffff; color: #1b5e20; border: 1px solid #a5d6a7; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 8px;">${escapeHtml(w)}</span>`).join('') : '<span style="font-size: 0.78rem; color: #5f6368; font-style: italic;">No write paths configured</span>'}
                                            </div>
                                        </div>
                                    </div>
                                    ${p.access_notes ? `<div style="font-size: 0.8rem; color: #3c4043; margin-top: 0.6rem; line-height: 1.4; background: #f8fafd; padding: 0.45rem 0.65rem; border-radius: 8px; border: 1px solid #c2e7ff;">ℹ️ <strong>Scope Notes:</strong> ${escapeHtml(p.access_notes)}</div>` : ''}
                                </div>
                            </div>
                            <div>
                                <strong style="font-size: 0.78rem; color: #5f6368; text-transform: uppercase; letter-spacing: 0.04em; display: block; margin-bottom: 0.4rem;">🛠️ MOST USED & PREFERRED SKILLS:</strong>
                                <div style="background: #ffffff; border: 1px solid #e1e3e1; border-radius: 14px; padding: 0.85rem 1rem;">
                                    <div style="display: flex; flex-wrap: wrap; gap: 0.45rem;">
                                        ${(p.skills && p.skills.length > 0) ? p.skills.map(s => `
                                            <span style="font-size: 0.82rem; background: #e8f0fe; color: #0b57d0; border: 1px solid #c2e7ff; font-weight: 600; padding: 0.25rem 0.65rem; border-radius: 10px; display: inline-flex; align-items: center; gap: 0.35rem;">
                                                ${escapeHtml(s)}
                                            </span>
                                        `).join('') : '<span style="font-size: 0.82rem; color: #5f6368; font-style: italic;">No preferred skills listed yet</span>'}
                                    </div>
                                </div>
                            </div>
                            <div>
                                <strong style="font-size: 0.78rem; color: #5f6368; text-transform: uppercase; letter-spacing: 0.04em; display: block; margin-bottom: 0.4rem;">📜 My experience:</strong>
                                ${p.resume && p.resume.length > 0 ? `
                                    <div style="display: flex; flex-direction: column; gap: 0.6rem;">
                                        ${p.resume.map(r => `
                                            <div style="background: #f8fafd; border: 1px solid #e1e3e1; border-radius: 12px; padding: 0.75rem 0.9rem;">
                                                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.4rem;">
                                                    <span style="font-weight: 600; font-size: 0.92rem; color: #1f1f1f; cursor: pointer;" onclick="selectChannel('${r.project_id}', '${escapeHtml(r.project_name)}', '${r.project_id === 'lantern' ? '🏞️' : '🚀'}')">
                                                        ${r.project_id === 'lantern' ? '🏞️' : '🚀'} ${escapeHtml(r.project_name)} ↗
                                                    </span>
                                                    <span style="font-size: 0.75rem; color: #0b57d0; background: #e8f0fe; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 10px;">
                                                        ${escapeHtml(r.role)}
                                                    </span>
                                                </div>
                                                ${r.period ? `<div style="font-size: 0.75rem; color: #5f6368; margin-top: 0.2rem;">${ICON_CLOCK}${escapeHtml(r.period)}</div>` : ''}
                                                ${r.highlights ? `<p style="font-size: 0.85rem; color: #3c4043; margin-top: 0.35rem; line-height: 1.4;">${escapeHtml(r.highlights)}</p>` : ''}
                                            </div>
                                        `).join('')}
                                    </div>
                                ` : `<p style="font-size: 0.85rem; color: #5f6368; font-style: italic;">No project resume items added yet.</p>`}
                            </div>
                        </div>
                    `;
                    threadEl.appendChild(profCard);
                }
                filteredTxs = currentHistory;
            } else if (activeChannel.startsWith('sleeve_')) {
                const sId = activeChannel.replace('sleeve_', '');
                const s = currentEnginesData.find(x => x.id === sId);
                if (s) {
                    const coreCard = document.createElement('div');
                    coreCard.style.cssText = "background: #f8fafd; border: 1px solid #e1e3e1; border-radius: 18px; padding: 1.5rem; margin-bottom: 1.5rem;";

                    const isModelCore = (s.category === 'model') || (!s.category && (s.id === 'vertex-ai' || s.id === 'ollama-local' || s.id === 'antigravity-queue'));
                    const isAgentCore = (s.category === 'agent') || (!s.category && s.id === 'google-adk');
                    const isContributorCore = (s.category === 'contributor') || (!s.category && s.id === 'human');
                    const isSyncedCore = (s.id === 'vertex-ai' || s.id === 'antigravity-queue' || s.id === 'google-adk' || s.type === 'vertex-ai' || s.type === 'antigravity-queue' || s.type === 'google-adk');

                    let badgeBg = '#e8f0fe';
                    let badgeColor = '#0b57d0';
                    let categoryBadgeText = '🏷️ Model Provider Core';
                    let primaryActionText = '➕ Add Model to Core';
                    let primaryActionHandler = `openAddModelToEngineModal('${s.id}')`;

                    if (isAgentCore) {
                        badgeBg = '#f3e5f5'; badgeColor = '#6a1b9a';
                        categoryBadgeText = '🤖 Agent Runtime Core';
                        primaryActionText = '';
                        primaryActionHandler = '';
                    } else if (isContributorCore) {
                        badgeBg = '#fce8e6'; badgeColor = '#c5221f';
                        categoryBadgeText = '🧭 Human Core';
                        primaryActionText = '';
                        primaryActionHandler = '';
                    }

                    const models = s.models || [];
                    let contentGridHtml = '';

                    if (isModelCore) {
                        // RENDER MODELS GRID
                        if (models.length === 0) {
                            contentGridHtml = `
                                <div style="text-align: center; color: #5f6368; padding: 2rem 1rem; border: 2px dashed #dadce0; border-radius: 12px; background: #ffffff;">
                                    <div style="font-size: 1.5rem; margin-bottom: 0.3rem;">🤖</div>
                                    <div style="font-weight: 600; font-size: 0.95rem; color: #1f1f1f;">No Models Configured in this Core</div>
                                    <div style="font-size: 0.8rem; color: #5f6368; margin-top: 0.2rem;">${s.id === 'vertex-ai' ? 'Sync foundation models directly from your GCP project.' : (s.id === 'antigravity-queue' ? 'Sync official models directly from Google Antigravity documentation.' : 'Register model checkpoints for this runtime.')}</div>
                                    ${s.id === 'vertex-ai' ? `
                                        <button class="btn-send" onclick="syncVertexDirectly(this)" style="margin-top: 0.8rem; padding: 0.4rem 1rem; font-size: 0.82rem; background: #1a73e8;">🔄 Sync with Google Model Garden</button>
                                    ` : (s.id === 'antigravity-queue' ? `
                                        <button class="btn-send" onclick="syncAntigravityDirectly(this)" style="margin-top: 0.8rem; padding: 0.4rem 1rem; font-size: 0.82rem; background: #202124;">🔄 Sync with Antigravity</button>
                                    ` : `
                                        <button class="btn-send" onclick="openAddModelToEngineModal('${s.id}')" style="margin-top: 0.8rem; padding: 0.4rem 1rem; font-size: 0.82rem;">➕ Add Model to Core</button>
                                    `)}
                                </div>
                            `;
                        } else {
                            contentGridHtml = `
                                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 0.85rem; margin-top: 0.4rem;">
                                    ${models.map(m => {
                                        return `
                                            <div style="background: #ffffff; border: 1px solid #c2e7ff; border-radius: 14px; padding: 1rem; display: flex; flex-direction: column; gap: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                                                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                                    <div>
                                                        <strong style="font-size: 0.98rem; color: #1f1f1f;">${escapeHtml(m.name)}</strong>
                                                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #5f6368; margin-top: 0.15rem;">
                                                            ID: <code>${escapeHtml(m.model_id || m.id)}</code>
                                                        </div>
                                                    </div>
                                                    ${!isSyncedCore ? `<button onclick="removeModelFromEngine('${s.id}', '${m.id}')" title="Remove model" style="background: none; border: none; font-size: 0.85rem; color: #d93025; cursor: pointer; padding: 0.1rem 0.35rem;">✕</button>` : ''}
                                                </div>

                                                <div style="font-size: 0.82rem; color: #3c4043; line-height: 1.4;">
                                                    ${escapeHtml(m.description || 'No description provided.')}
                                                </div>
                                            </div>
                                        `;
                                    }).join('')}
                                </div>
                            `;
                        }
                    } else if (isAgentCore) {
                        // RENDER ADK AGENTS GRID
                        const sleeveAgents = currentAgentsData.filter(a => (a.provider && (a.provider.type === s.id || a.provider.type === s.type)) || a.engine === s.id);
                        
                        if (sleeveAgents.length === 0) {
                            contentGridHtml = `
                                <div style="text-align: center; color: #5f6368; padding: 2.5rem 1rem; border: 2px dashed #ce93d8; border-radius: 14px; background: #ffffff;">
                                    <div style="font-size: 2rem; margin-bottom: 0.3rem;">🔮</div>
                                    <div style="font-weight: 700; font-size: 1rem; color: #1f1f1f;">No ADK Agents Registered to this Core</div>
                                    <div style="font-size: 0.82rem; color: #5f6368; margin-top: 0.25rem;">Sync or discover autonomous agent harnesses powered by the Google ADK runtime.</div>
                                    <button class="btn-send" onclick="syncGoogleAdkDirectly(this)" style="margin-top: 0.9rem; padding: 0.45rem 1.1rem; font-size: 0.84rem; background: #673ab7;">🔄 Sync with Google ADK</button>
                                </div>
                            `;
                        } else {
                            contentGridHtml = `
                                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; margin-top: 0.5rem;">
                                    ${sleeveAgents.map(a => {
                                        const skills = a.skills || [];
                                        const skillsChips = skills.length > 0
                                            ? skills.map(sk => `<span style="background: #f3e5f5; color: #6a1b9a; border: 1px solid #e1bee7; border-radius: 6px; padding: 0.15rem 0.45rem; font-size: 0.72rem; font-weight: 500;">${escapeHtml(sk)}</span>`).join(' ')
                                            : '<span style="font-size: 0.72rem; color: #888; font-style: italic;">Standard ADK Toolkit</span>';

                                        const foundationModel = (a.provider && a.provider.model) || 'Gemini 3.7 Flash';

                                        return `
                                            <div style="background: #ffffff; border: 1px solid #ce93d8; border-radius: 14px; padding: 1.15rem; display: flex; flex-direction: column; gap: 0.7rem; box-shadow: 0 1px 4px rgba(106, 27, 154, 0.06);">
                                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                                    <div style="display: flex; gap: 0.65rem; align-items: center;">
                                                        <div style="width: 42px; height: 42px; border-radius: 10px; background: #f3e5f5; display: flex; align-items: center; justify-content: center; font-size: 1.5rem;">
                                                            ${a.icon || '🔮'}
                                                        </div>
                                                        <div>
                                                            <strong style="font-size: 1.05rem; color: #1f1f1f;">${escapeHtml(a.name)}</strong>
                                                            <div style="font-size: 0.76rem; color: #6a1b9a; font-weight: 600;">${escapeHtml(a.role || 'Autonomous Systems Specialist')}</div>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div style="background: #f8fafd; border: 1px solid #edf2f7; border-radius: 8px; padding: 0.55rem 0.75rem; font-size: 0.78rem; display: flex; align-items: center; justify-content: space-between;">
                                                    <span>⚡ <strong>Model:</strong></span>
                                                    <span style="color: #6a1b9a; font-weight: 700;">${escapeHtml(foundationModel)}</span>
                                                </div>

                                                ${a.system_prompt ? `
                                                    <div>
                                                        <div style="font-size: 0.7rem; font-weight: 700; color: #5f6368; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.2rem;">Default Behavioral Directives:</div>
                                                        <div style="font-size: 0.78rem; color: #3c4043; background: #fafafa; border: 1px solid #e1e3e1; border-radius: 8px; padding: 0.5rem 0.65rem; line-height: 1.4; max-height: 75px; overflow-y: auto;">
                                                            "${escapeHtml(a.system_prompt)}"
                                                        </div>
                                                    </div>
                                                ` : ''}

                                                <div style="margin-top: auto; padding-top: 0.4rem; border-top: 1px solid #edf2f7; display: flex; flex-direction: column; gap: 0.25rem;">
                                                    <div style="font-size: 0.7rem; font-weight: 700; color: #5f6368; text-transform: uppercase; letter-spacing: 0.04em;">Declared Skills & Toolsets:</div>
                                                    <div style="display: flex; flex-wrap: wrap; gap: 0.25rem;">
                                                        ${skillsChips}
                                                    </div>
                                                </div>
                                            </div>
                                        `;
                                    }).join('')}
                                </div>
                            `;
                        }
                    } else {
                        // Contributor Core has no sub-grid list
                        contentGridHtml = '';
                    }

                    const sleeveAgents = currentAgentsData.filter(a => (a.provider && (a.provider.type === s.id || a.provider.type === s.type)) || a.engine === s.id);

                    const sectionTitle = isModelCore
                        ? `🤖 Supported Models & Checkpoints (${models.length}):`
                        : isAgentCore
                        ? `🤖 Registered Autonomous ADK Agents (${sleeveAgents.length}):`
                        : '';

                    coreCard.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
                            <div style="display: flex; gap: 1rem; align-items: center;">
                                <div style="width: 56px; height: 56px; border-radius: 50%; background: #ffffff; display: flex; align-items: center; justify-content: center; font-size: 2rem; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                                    ${s.icon || '🥋'}
                                </div>
                                <div>
                                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                                        <h2 style="font-size: 1.3rem; font-weight: 700; margin: 0;">${escapeHtml(s.name)}</h2>
                                        <span style="background: ${badgeBg}; color: ${badgeColor}; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 10px;">${categoryBadgeText}</span>
                                    </div>
                                    <div style="font-size: 0.8rem; color: #5f6368; margin-top: 0.3rem; display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap;">
                                        ${isModelCore ? `<span>🤖 Models: <strong>${models.length}</strong></span>` : isAgentCore ? `<span>🤖 ADK Agents: <strong>${sleeveAgents.length}</strong></span>` : ''}
                                        <span style="color: #1b5e20; background: #e8f5e9; padding: 0.1rem 0.5rem; border-radius: 8px; font-weight: 600; font-size: 0.75rem;">🟢 Active Runtime</span>
                                    </div>
                                </div>
                            </div>
                            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                                ${(s.id === 'vertex-ai' || s.type === 'vertex-ai') ? `<button class="btn-send" style="padding: 0.45rem 0.9rem; font-size: 0.82rem; background: #1a73e8;" onclick="syncVertexDirectly(this)">🔄 Sync with Google Model Garden</button>` : ''}
                                ${(s.id === 'antigravity-queue' || s.type === 'antigravity-queue') ? `<button class="btn-send" style="padding: 0.45rem 0.9rem; font-size: 0.82rem; background: #202124; color: #ffffff;" onclick="syncAntigravityDirectly(this)">🔄 Sync with Antigravity</button>` : ''}
                                ${(s.id === 'google-adk' || s.type === 'google-adk') ? `<button class="btn-send" style="padding: 0.45rem 0.9rem; font-size: 0.82rem; background: #673ab7;" onclick="syncGoogleAdkDirectly(this)">🔄 Sync with Google ADK</button>` : ''}
                                ${(isModelCore && s.id !== 'vertex-ai' && s.type !== 'vertex-ai' && s.id !== 'antigravity-queue' && s.type !== 'antigravity-queue') ? `<button class="btn-send" style="padding: 0.45rem 0.9rem; font-size: 0.82rem;" onclick="${primaryActionHandler}">${primaryActionText}</button>` : ''}
                            </div>
                        </div>

                        <div style="display: flex; flex-direction: column; gap: 1rem; margin-top: 1.25rem;">
                            <div>
                                <strong style="font-size: 0.78rem; color: #5f6368; text-transform: uppercase; letter-spacing: 0.04em; display: block; margin-bottom: 0.35rem;">Runtime Capabilities & Description:</strong>
                                <div style="background: #ffffff; border: 1px solid #e1e3e1; border-radius: 12px; padding: 0.9rem 1.1rem; font-size: 0.86rem; color: #3c4043; line-height: 1.5;">
                                    ${escapeHtml(s.description || 'No description provided for this core runtime.')}
                                </div>
                            </div>

                            ${(isModelCore || isAgentCore) ? `
                                <div>
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                                        <strong style="font-size: 0.78rem; color: #5f6368; text-transform: uppercase; letter-spacing: 0.04em;">${sectionTitle}</strong>
                                    </div>
                                    ${contentGridHtml}
                                </div>
                            ` : ''}
                        </div>
                    `;

                    threadEl.appendChild(coreCard);
                }
                return;
            } else if (activeChannel === 'lantern' || activeChannel.startsWith('proj_')) {
                // Project spaces (Lantern, Bridge Deck, etc.) show all team room messages & interactions.
                // Excludes personal notes streams!
                filteredTxs = currentHistory.filter(tx => {
                    if (!tx.mode) return true;
                    if (typeof tx.mode === 'string' && (tx.mode.startsWith('prof_') || tx.mode.endsWith('_notes'))) return false;
                    return true;
                });
            } else if (activeChannel.endsWith('_notes')) {
                filteredTxs = currentHistory.filter(tx => tx.mode === activeChannel || (tx.recipient_role && tx.recipient_role.includes('Notes') && tx.mode === activeChannel));
            } else if (activeChannel === 'astra_direct') {
                filteredTxs = currentHistory.filter(tx => tx.mode === 'astra_direct' || (tx.recipient && tx.recipient.includes('Astra') && tx.mode !== 'antigravity_impl' && !tx.mode.endsWith('_notes')));
            } else if (activeChannel === 'vector_direct') {
                filteredTxs = currentHistory.filter(tx => tx.mode === 'vector_direct');
            } else if (activeChannel === 'claude_direct') {
                filteredTxs = currentHistory.filter(tx => tx.mode === 'claude_direct');
            }

            if (filteredTxs.length === 0) {
                if (activeChannel.startsWith('prof_')) {
                    const emptyDiv = document.createElement('div');
                    emptyDiv.style.cssText = "text-align: center; color: #5f6368; padding: 2.5rem 1rem; border: 2px dashed #e1e3e1; border-radius: 16px; margin-top: 1rem;";
                    emptyDiv.innerHTML = `
                        <div style="font-size: 1.8rem; margin-bottom: 0.5rem;">📝</div>
                        <div style="font-weight: 600; font-size: 1rem; color: #1f1f1f;">Personal Notes & Thought Log Stream</div>
                        <div style="font-size: 0.84rem; color: #5f6368; margin-top: 0.3rem;">Type a note in the prompt bar below to post thoughts or task logs directly to this profile thread.</div>
                    `;
                    threadEl.appendChild(emptyDiv);
                } else {
                    threadEl.innerHTML = `
                        <div style="text-align: center; color: var(--text-muted); padding: 3rem;">
                            No messages yet in this channel. Send a prompt or note below!
                        </div>
                    `;
                }
                return;
            }

            const seenMessageBodies = new Set();

            filteredTxs.forEach(tx => {
                const turnDiv = document.createElement('div');
                turnDiv.className = 'turn-group';
                turnDiv.id = tx.id;
                const formattedTime = formatLocalTimestamp(tx.timestamp);

                const isAutoDispatched = Boolean(tx.a2a_meta && tx.a2a_meta.auto_dispatched);
                const hasAgentResponse = Boolean(tx.claude_response || tx.antigravity_response || tx.response_text);
                const promptBodyTrimmed = (tx.prompt_text || '').trim();

                // 1. User / Prompt Row
                // Suppress prompt row if:
                // a) this exact prompt text was already displayed in the thread by another turn, OR
                // b) it is an auto-dispatched turn that has a response (because the prompt was already the sender's response in the prior turn)
                let userRowHtml = '';
                if (promptBodyTrimmed && !seenMessageBodies.has(promptBodyTrimmed) && (!isAutoDispatched || !hasAgentResponse)) {
                    seenMessageBodies.add(promptBodyTrimmed);
                    const userMeta = getAgentMeta(tx.sender || 'Team Lead', tx.sender_role || 'Project Lead');
                    userRowHtml = `
                        <div class="chat-row">
                            <div class="chat-avatar" onclick="showMemberPersonaPopover(event, '${userMeta.id}', '${activeChannel}')" title="Click to view ${escapeHtml(userMeta.name)}'s personality persona">${userMeta.avatar}</div>
                            <div class="chat-content">
                                <div class="chat-meta">
                                    <span class="author-name" onclick="showMemberPersonaPopover(event, '${userMeta.id}', '${activeChannel}')" style="cursor: pointer;" title="Click to view ${escapeHtml(userMeta.name)}'s personality persona">${escapeHtml(userMeta.name)}</span>
                                    <span class="chat-timestamp">${formattedTime}</span>
                                    <span class="role-badge ${userMeta.badgeClass}">${escapeHtml(userMeta.role)}</span>
                                </div>
                                <div class="chat-bubble ${userMeta.bubbleClass}">
                                    <div class="msg-formatted">${formatMarkdownText(tx.prompt_text)}</div>
                                </div>
                                ${renderReactionsHtml(tx, 'prompt')}
                            </div>
                        </div>
                    `;
                }

                // 2. Vector / Astra Response Row
                const isAstraTarget = (tx.recipient && tx.recipient.includes('Astra')) || tx.mode === 'astra_direct' || (tx.sender && tx.sender.includes('Astra'));
                const agMeta = getAgentMeta(isAstraTarget ? 'Astra (Antigravity)' : 'Vector (Implementation Lead)', isAstraTarget ? 'Bridge Deck Lead' : 'Implementation Lead');
                const agResponseTrimmed = (tx.antigravity_response || '').trim();
                const isAgPending = agResponseTrimmed && (agResponseTrimmed.includes('⏳') || agResponseTrimmed.includes('Awaiting') || agResponseTrimmed.includes('Relayed'));
                const hasCompletedAgentResponse = Boolean(tx.claude_response || tx.response_text);
                const agBubbleClass = isAgPending ? 'bubble-agent bubble-pending' : 'bubble-agent';
                let agRowHtml = '';
                if (agResponseTrimmed && (!isAgPending || !hasCompletedAgentResponse) && (isAgPending || !seenMessageBodies.has(agResponseTrimmed))) {
                    if (!isAgPending) seenMessageBodies.add(agResponseTrimmed);
                    agRowHtml = `
                        <div class="chat-row">
                            <div class="chat-avatar" onclick="showMemberPersonaPopover(event, '${agMeta.id}', '${activeChannel}')" title="Click to view ${escapeHtml(agMeta.name)}'s personality persona">${agMeta.avatar}</div>
                            <div class="chat-content">
                                <div class="chat-meta">
                                    <span class="author-name" onclick="showMemberPersonaPopover(event, '${agMeta.id}', '${activeChannel}')" style="cursor: pointer;" title="Click to view ${escapeHtml(agMeta.name)}'s personality persona">${escapeHtml(agMeta.name)}</span>
                                    <span class="chat-timestamp">${formattedTime}</span>
                                    <span class="role-badge ${agMeta.badgeClass}">${escapeHtml(agMeta.role)}</span>
                                </div>
                                <div class="chat-bubble ${agBubbleClass}">
                                    <div class="msg-formatted">${formatMarkdownText(tx.antigravity_response)}</div>
                                </div>
                                ${renderReactionsHtml(tx, 'antigravity')}
                            </div>
                        </div>
                    `;
                }

                // 3. Dynamic Agent Response Row
                let responderName = tx.recipient || 'Lumen (Claude Opus 5)';
                let responderRole = tx.recipient_role || 'Scientific Advisor';
                if (tx.target_agent_id) {
                    const targetProf = currentProfiles.find(x => x.id === tx.target_agent_id);
                    if (targetProf) {
                        responderName = targetProf.name;
                        responderRole = targetProf.role || targetProf.model || 'Team Member';
                    }
                } else if (tx.mode === 'astra_direct' || (tx.recipient && tx.recipient.includes('Astra'))) {
                    responderName = 'Astra (Gemini 3.7 Flash)';
                    responderRole = 'Bridge Deck Lead';
                } else if (tx.mode === 'vector_direct' || (tx.recipient && tx.recipient.includes('Vector'))) {
                    responderName = 'Vector (Implementation Lead)';
                    responderRole = 'Implementation Lead';
                } else if (tx.mode === 'claude_direct' || (tx.recipient && tx.recipient.includes('Lumen'))) {
                    responderName = 'Lumen (Claude Opus 5)';
                    responderRole = 'Scientific Advisor';
                } else if (tx.mode === 'lead_notes') {
                    responderName = 'Team Lead';
                    responderRole = 'Research Manager';
                } else if (tx.mode && tx.mode.endsWith('_direct')) {
                    const dynamicId = tx.mode.replace('_direct', '');
                    const dynProf = currentProfiles.find(x => x.id === dynamicId);
                    if (dynProf) {
                        responderName = dynProf.name;
                        responderRole = dynProf.role || dynProf.model || 'Team Member';
                    }
                } else if (tx.mode === 'test5_direct' || (tx.recipient && tx.recipient.includes('Test 5'))) {
                    responderName = 'Test 5 Agent';
                    responderRole = 'Acceptance Test Evaluator';
                }
                const modelMeta = getAgentMeta(responderName, responderRole);
                const modelText = (tx.claude_response || tx.response_text || '').trim();
                const isModelPending = modelText && (modelText.includes('⏳') || modelText.includes('Awaiting') || modelText.includes('evaluating'));
                const modelBubbleClass = isModelPending ? 'bubble-agent bubble-pending' : 'bubble-agent';

                let claudeRowHtml = '';
                if (modelText && (isModelPending || !seenMessageBodies.has(modelText))) {
                    if (!isModelPending) seenMessageBodies.add(modelText);
                    claudeRowHtml = `
                        <div class="chat-row">
                            <div class="chat-avatar" onclick="showMemberPersonaPopover(event, '${modelMeta.id}', '${activeChannel}')" title="Click to view ${escapeHtml(modelMeta.name)}'s personality persona">${modelMeta.avatar}</div>
                            <div class="chat-content">
                                <div class="chat-meta">
                                    <span class="author-name" onclick="showMemberPersonaPopover(event, '${modelMeta.id}', '${activeChannel}')" style="cursor: pointer;" title="Click to view ${escapeHtml(modelMeta.name)}'s personality persona">${escapeHtml(modelMeta.name)}</span>
                                    <span class="chat-timestamp">${formattedTime}</span>
                                    <span class="role-badge ${modelMeta.badgeClass}">${escapeHtml(modelMeta.role)}</span>
                                </div>
                                <div class="chat-bubble ${modelBubbleClass}">
                                    <div class="msg-formatted">${formatMarkdownText(modelText)}</div>
                                </div>
                                ${renderReactionsHtml(tx, 'claude')}
                            </div>
                        </div>
                    `;
                }

                let pendingLoaderHtml = '';
                if (tx.is_pending && !tx.antigravity_response && !modelText) {
                    pendingLoaderHtml = `
                        <div class="chat-row" style="margin-top: 0.35rem;">
                            <div class="chat-avatar" onclick="showMemberPersonaPopover(event, '${modelMeta.id}', '${activeChannel}')" title="Click to view ${escapeHtml(modelMeta.name)}'s personality persona">${modelMeta.avatar || '🤖'}</div>
                            <div class="chat-content">
                                <div class="chat-meta">
                                    <span class="author-name" onclick="showMemberPersonaPopover(event, '${modelMeta.id}', '${activeChannel}')" style="cursor: pointer;" title="Click to view ${escapeHtml(modelMeta.name)}'s personality persona">${escapeHtml(modelMeta.name)}</span>
                                    <span class="role-badge ${modelMeta.badgeClass}">${escapeHtml(modelMeta.role)}</span>
                                </div>
                                <div class="chat-bubble typing-bubble">
                                    <div class="gchat-typing-dots">
                                        <span class="dot"></span>
                                        <span class="dot"></span>
                                        <span class="dot"></span>
                                    </div>
                                    <span style="font-size: 0.83rem; color: #5f6368; font-style: italic;">${escapeHtml(modelMeta.name.split(' ')[0])} is thinking...</span>
                                </div>
                            </div>
                        </div>
                    `;
                }

                const turnContent = `${userRowHtml}${agRowHtml}${claudeRowHtml}${pendingLoaderHtml}`.trim();
                if (turnContent) {
                    turnDiv.innerHTML = turnContent;
                    threadEl.appendChild(turnDiv);
                }
            });

            // Google Chat Live A2A Thinking / Generation Indicator
            if (latestA2AActiveTask && (latestA2AActiveTask.project_id === activeChannel || (activeChannel === 'lantern' && latestA2AActiveTask.project_id === 'lantern') || (activeChannel.replace('proj_', '') === latestA2AActiveTask.project_id.replace('proj_', '')))) {
                const targetId = latestA2AActiveTask.target;
                const targetProf = currentProfiles.find(x => x.id === targetId);
                const targetName = targetProf ? targetProf.name : (targetId.charAt(0).toUpperCase() + targetId.slice(1));
                const targetRole = targetProf ? (targetProf.role || targetProf.model || 'Autonomous Agent') : 'Autonomous Agent';
                const targetMeta = getAgentMeta(targetName, targetRole);
                const senderName = latestA2AActiveTask.sender || 'Teammate';

                const a2aTypingDiv = document.createElement('div');
                a2aTypingDiv.className = 'turn-group';
                a2aTypingDiv.id = 'liveA2ATypingIndicator';
                a2aTypingDiv.innerHTML = `
                    <div class="chat-row" style="margin-top: 0.35rem;">
                        <div class="chat-avatar" onclick="showMemberPersonaPopover(event, '${targetMeta.id}', '${activeChannel}')" title="Click to view ${escapeHtml(targetMeta.name)}'s personality persona">${targetMeta.avatar || '🤖'}</div>
                        <div class="chat-content">
                            <div class="chat-meta">
                                <span class="author-name" onclick="showMemberPersonaPopover(event, '${targetMeta.id}', '${activeChannel}')" style="cursor: pointer;" title="Click to view ${escapeHtml(targetMeta.name)}'s personality persona">${escapeHtml(targetMeta.name)}</span>
                                <span class="role-badge ${targetMeta.badgeClass}">${escapeHtml(targetMeta.role)}</span>
                                <span style="font-size: 0.72rem; color: #0b57d0; font-weight: 600; background: #e8f0fe; padding: 0.1rem 0.45rem; border-radius: 8px; border: 1px solid #c2e7ff;">⚡ Live A2A Cascade</span>
                            </div>
                            <div class="chat-bubble typing-bubble">
                                <div class="gchat-typing-dots">
                                    <span class="dot"></span>
                                    <span class="dot"></span>
                                    <span class="dot"></span>
                                </div>
                                <span style="font-size: 0.83rem; color: #5f6368; font-style: italic;">${escapeHtml(targetMeta.name.split(' ')[0])} is thinking... (responding to ${escapeHtml(senderName)})</span>
                            </div>
                        </div>
                    </div>
                `;
                threadEl.appendChild(a2aTypingDiv);
            }
        }

        function renderMentionAutocomplete(query = '') {
            const popup = document.getElementById('mentionAutocomplete');
            const container = document.getElementById('mentionListContainer');
            if (!popup || !container) return;

            const lowerQuery = (query || '').toLowerCase().trim();
            const profiles = (currentProfiles && currentProfiles.length > 0) ? currentProfiles : DEFAULT_PROFILES;

            // Check if active channel is a project room
            let projectMemberIds = [];
            if (activeChannel === 'lantern' || activeChannel.startsWith('proj_')) {
                const pObj = currentProjects.find(x => x.id === activeChannel) || currentProjects.find(x => x.id === activeChannel.replace('proj_', ''));
                if (pObj && Array.isArray(pObj.members)) {
                    projectMemberIds = pObj.members;
                }
            }

            const filtered = profiles.filter(p => {
                if (!lowerQuery) return true;
                const idMatch = (p.id || '').toLowerCase().includes(lowerQuery);
                const nameMatch = (p.name || '').toLowerCase().includes(lowerQuery);
                const modelName = getModelDisplayName(p).toLowerCase();
                const modelMatch = modelName.includes(lowerQuery) || (p.model || '').toLowerCase().includes(lowerQuery);
                const roleMatch = (p.role || '').toLowerCase().includes(lowerQuery);
                return idMatch || nameMatch || modelMatch || roleMatch;
            });

            if (filtered.length === 0) {
                currentMentionFilteredProfiles = [];
                popup.style.display = 'none';
                return;
            }

            // Sort: members assigned to this project room first, then alphabetical
            filtered.sort((a, b) => {
                if (projectMemberIds.length > 0) {
                    const aIn = projectMemberIds.includes(a.id);
                    const bIn = projectMemberIds.includes(b.id);
                    if (aIn && !bIn) return -1;
                    if (!aIn && bIn) return 1;
                }
                return (a.name || a.id).localeCompare(b.name || b.id);
            });

            currentMentionFilteredProfiles = filtered;
            activeMentionIndex = 0; // Highlight top match by default

            container.innerHTML = '';
            filtered.forEach((p, idx) => {
                const item = document.createElement('div');
                item.className = 'mention-item';
                const isSelected = (idx === activeMentionIndex);
                item.style.cssText = `padding: 0.5rem 0.75rem; font-size: 0.88rem; cursor: pointer; display: flex; align-items: center; gap: 0.55rem; transition: background 0.15s ease; border-bottom: 1px solid #f1f3f4; background: ${isSelected ? '#e8f0fe' : 'transparent'};`;
                item.onmouseenter = () => {
                    activeMentionIndex = idx;
                    updateMentionSelectionStyles();
                };

                const modelDisplayName = getModelDisplayName(p);
                const mentionHandle = '@' + p.id;
                const isHuman = (p.id === 'lead' || p.engine === 'human');
                const badgeBg = isHuman ? '#fce8e6' : '#e8f0fe';
                const badgeColor = isHuman ? '#c5221f' : '#0b57d0';
                const badgeBorder = isHuman ? '#f5c2c7' : '#c2e7ff';
                const badgeIcon = isHuman ? '🧭' : '⚡';

                item.innerHTML = `
                    <span style="font-size: 1.15rem; flex-shrink: 0;">${p.avatar || '👤'}</span>
                    <div style="display: flex; align-items: center; gap: 0.35rem; min-width: 0;">
                        <strong style="color: ${isSelected ? '#0b57d0' : '#1f1f1f'}; font-size: 0.88rem;">${escapeHtml(mentionHandle)}</strong>
                        <span style="font-size: 0.78rem; color: #5f6368; white-space: nowrap;">(${escapeHtml(p.name)})</span>
                    </div>
                    <span style="font-size: 0.73rem; color: ${badgeColor}; background: ${badgeBg}; border: 1px solid ${badgeBorder}; padding: 0.12rem 0.45rem; border-radius: 8px; font-weight: 600; margin-left: auto; max-width: 135px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: inline-flex; align-items: center; gap: 0.25rem; flex-shrink: 0;">
                        <span>${badgeIcon}</span> <span>${escapeHtml(modelDisplayName)}</span>
                    </span>
                `;
                item.onclick = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    insertMention(mentionHandle + ' ');
                };
                container.appendChild(item);
            });

            popup.style.display = 'block';
        }

        function updateMentionSelectionStyles() {
            const container = document.getElementById('mentionListContainer');
            if (!container) return;
            const items = container.querySelectorAll('.mention-item');
            items.forEach((it, idx) => {
                const isSelected = (idx === activeMentionIndex);
                it.style.background = isSelected ? '#e8f0fe' : 'transparent';
                const strong = it.querySelector('strong');
                if (strong) strong.style.color = isSelected ? '#0b57d0' : 'inherit';
                if (isSelected) {
                    it.scrollIntoView({ block: 'nearest' });
                }
            });
        }

        const promptInputEl = document.getElementById('promptInput');
        promptInputEl.addEventListener('input', (e) => {
            autoResizeTextarea(promptInputEl);

            const val = promptInputEl.value;
            const cursorPos = promptInputEl.selectionStart;
            const lastAt = val.lastIndexOf('@', cursorPos - 1);
            
            if (lastAt !== -1 && (lastAt === 0 || val[lastAt - 1] === ' ' || val[lastAt - 1] === '\n')) {
                const query = val.slice(lastAt + 1, cursorPos);
                if (!query.includes(' ') && !query.includes('\n')) {
                    renderMentionAutocomplete(query);
                    return;
                }
            }
            document.getElementById('mentionAutocomplete').style.display = 'none';
        });

        promptInputEl.addEventListener('keydown', (e) => {
            const popup = document.getElementById('mentionAutocomplete');
            const isPopupOpen = popup && popup.style.display !== 'none' && currentMentionFilteredProfiles.length > 0;

            if (isPopupOpen) {
                if (e.key === 'Tab' || (e.key === 'Enter' && !e.shiftKey)) {
                    e.preventDefault();
                    e.stopPropagation();
                    const targetProfile = currentMentionFilteredProfiles[activeMentionIndex] || currentMentionFilteredProfiles[0];
                    if (targetProfile) {
                        insertMention('@' + targetProfile.id + ' ');
                    }
                    return;
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    activeMentionIndex = (activeMentionIndex + 1) % currentMentionFilteredProfiles.length;
                    updateMentionSelectionStyles();
                    return;
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    activeMentionIndex = (activeMentionIndex - 1 + currentMentionFilteredProfiles.length) % currentMentionFilteredProfiles.length;
                    updateMentionSelectionStyles();
                    return;
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    popup.style.display = 'none';
                    return;
                }
            }

            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                document.getElementById('btnSend').click();
            }
        });

        function insertMention(mentionText) {
            const val = promptInputEl.value;
            const cursorPos = promptInputEl.selectionStart;
            const lastAt = val.lastIndexOf('@', cursorPos - 1);
            if (lastAt !== -1) {
                promptInputEl.value = val.slice(0, lastAt) + mentionText + val.slice(cursorPos);
            } else {
                promptInputEl.value += mentionText;
            }
            promptInputEl.focus();
            document.getElementById('mentionAutocomplete').style.display = 'none';
        }

        document.getElementById('btnSend').addEventListener('click', async () => {
            const promptInput = document.getElementById('promptInput');
            const prompt = promptInput.value.trim();
            const model = 'claude-opus-5';

            if (!prompt) {
                alert("Please enter a prompt text!");
                return;
            }

            const btn = document.getElementById('btnSend');
            btn.disabled = true;

            const lowerPrompt = prompt.toLowerCase();
            let effectiveMode = 'auto';
            let recipient = 'Astra (Antigravity)';
            let recipient_role = 'Bridge Deck Lead';

            // Dynamic mention resolution against all active team member profiles (@mention or natural prefix address e.g. "Lumen, ...")
            const mentionedProfiles = [];
            for (const p of currentProfiles) {
                const idTag = '@' + p.id.toLowerCase();
                const firstName = p.name.split(' ')[0].toLowerCase();
                const firstNameTag = '@' + firstName;
                const naturalPrefixComma = firstName + ',';
                const naturalPrefixColon = firstName + ':';
                const naturalPrefixSpace = firstName + ' ';

                if (lowerPrompt.includes(idTag) || 
                    lowerPrompt.includes(firstNameTag) ||
                    lowerPrompt.startsWith(naturalPrefixComma) ||
                    lowerPrompt.startsWith(naturalPrefixColon) ||
                    lowerPrompt.startsWith(naturalPrefixSpace)) {
                    if (!mentionedProfiles.some(m => m.id === p.id)) {
                        mentionedProfiles.push(p);
                    }
                }
            }

            // Legacy alias check for Lumen / Claude
            if (lowerPrompt.includes('@claude') || lowerPrompt.includes('@lumen') || lowerPrompt.startsWith('claude,') || lowerPrompt.startsWith('claude:')) {
                const lumenP = currentProfiles.find(x => x.id === 'lumen') || { id: 'lumen', name: 'Lumen (Claude Opus 5)', role: 'Scientific Advisor', engine: 'vertex-ai' };
                if (!mentionedProfiles.some(m => m.id === 'lumen')) {
                    mentionedProfiles.push(lumenP);
                }
            }

            let matchedMentionProfile = null;
            if (mentionedProfiles.length > 0) {
                // If multiple agents are mentioned (e.g. @lumen @astra), prioritize active automated engines for direct execution
                matchedMentionProfile = mentionedProfiles.find(p => p.engine && p.engine !== 'human' && p.engine !== 'antigravity-queue') || mentionedProfiles[0];
            }

            if (matchedMentionProfile) {
                if (matchedMentionProfile.id === 'lead') {
                    effectiveMode = 'lead_notes';
                    recipient = "Team Lead's Personal Notebook";
                    recipient_role = 'Personal Notes';
                } else {
                    effectiveMode = matchedMentionProfile.id + '_direct';
                    recipient = matchedMentionProfile.name;
                    const mentionRole = getMemberProjectRole(matchedMentionProfile, activeChannel);
                    recipient_role = mentionRole || matchedMentionProfile.role || 'Technical Member of Staff';
                }
            } else {
                // Auto-route based on activeChannel room
                if (activeChannel === 'lead_notes') {
                    effectiveMode = 'lead_notes';
                    recipient = "Team Lead's Personal Notebook";
                    recipient_role = 'Personal Notes';
                } else if (activeChannel.startsWith('prof_')) {
                    effectiveMode = activeChannel;
                    const pId = activeChannel.replace('prof_', '');
                    const pObj = currentProfiles.find(x => x.id === pId);
                    const pName = pObj ? pObj.name : pId;
                    recipient = `${pName}'s Personal Notes`;
                    recipient_role = 'Personal Thought Log';
                } else if (activeChannel === 'astra_direct') {
                    effectiveMode = 'astra_direct';
                    recipient = 'Astra';
                    recipient_role = getMemberProjectRole('astra', activeChannel) || 'Bridge Deck Lead';
                } else if (activeChannel === 'vector_direct') {
                    effectiveMode = 'vector_direct';
                    recipient = 'Vector';
                    recipient_role = getMemberProjectRole('vector', activeChannel) || 'Implementation Lead';
                } else if (activeChannel === 'claude_direct') {
                    effectiveMode = 'claude_direct';
                    recipient = 'Lumen';
                    recipient_role = getMemberProjectRole('lumen', activeChannel) || 'Scientific Advisor';
                } else {
                    // General Room Message in Project Workspace (no @mention)
                    const pObj = currentProjects.find(x => x.id === activeChannel);
                    effectiveMode = 'room';
                    recipient = pObj ? pObj.name : 'Project Room';
                    recipient_role = 'Team Room Stream';
                }
            }

            let currentProjId = activeChannel;
            const pObj = currentProjects.find(x => x.id === activeChannel);
            if (pObj) currentProjId = pObj.id;
            const humanProf = (currentProfiles || []).find(p => p.engine === 'human' || p.model === 'Human' || p.type === 'human' || p.id === 'lead');
            const senderId = humanProf ? humanProf.id : 'lead';
            const senderName = humanProf ? humanProf.name : 'Team Lead';
            const currentSenderRole = getMemberProjectRole(senderId, currentProjId) || 'Project Lead';

            const tempTxId = 'tx_pending_' + Date.now();
            const timeStr = new Date().toISOString();
            const pendingTx = {
                id: tempTxId,
                is_pending: true,
                timestamp: timeStr,
                mode: effectiveMode,
                target_agent_id: (effectiveMode.endsWith('_direct') ? effectiveMode.replace('_direct', '') : null),
                sender: senderName,
                sender_role: currentSenderRole,
                recipient: recipient,
                recipient_role: recipient_role,
                prompt_text: prompt,
                antigravity_response: (effectiveMode === 'astra_notes' || effectiveMode === 'vector_notes') ? `📌 *Note saved to ${recipient}:* ${prompt}` : null,
                claude_response: (effectiveMode === 'lumen_notes') ? `📌 *Note saved to ${recipient}:* ${prompt}` : null
            };

            currentHistory.push(pendingTx);
            projectHistoryCache[activeChannel] = currentHistory;
            renderChatThread();
            promptInput.value = '';
            autoResizeTextarea(promptInput);
            document.getElementById('mentionAutocomplete').style.display = 'none';
            scrollToBottom();

            try {
                const resp = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        prompt, mode: effectiveMode, model, location: 'global',
                        sender: senderName,
                        sender_role: currentSenderRole,
                        recipient, recipient_role,
                        project_id: currentProjId
                    })
                });
                const resData = await resp.json();
                if (resData.success) {
                    await fetchHistory(true);
                } else {
                    currentHistory = currentHistory.filter(t => t.id !== tempTxId);
                    projectHistoryCache[activeChannel] = currentHistory;
                    renderChatThread();
                    promptInput.value = prompt;
                    autoResizeTextarea(promptInput);
                    alert("Execution Error: " + (resData.error || "Unknown error"));
                }
            } catch (err) {
                currentHistory = currentHistory.filter(t => t.id !== tempTxId);
                renderChatThread();
                promptInput.value = prompt;
                autoResizeTextarea(promptInput);
                alert("Network / API Error: " + err);
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<span>Send</span> <span>➔</span>';
            }
        });

        // Full Categorized Emoji Library with Search & Filter
        const FULL_EMOJI_LIST = [
            // Moon, Sun, Nature, Space & Weather
            { char: '🌙', name: 'crescent moon night lunar space sleep', cat: 'nature' },
            { char: '🌕', name: 'full moon night lunar space astronomy', cat: 'nature' },
            { char: '🌖', name: 'waning gibbous moon lunar space', cat: 'nature' },
            { char: '🌗', name: 'last quarter moon lunar space', cat: 'nature' },
            { char: '🌘', name: 'waning crescent moon lunar space', cat: 'nature' },
            { char: '🌑', name: 'new moon lunar dark space astronomy', cat: 'nature' },
            { char: '🌒', name: 'waxing crescent moon lunar space', cat: 'nature' },
            { char: '🌓', name: 'first quarter moon lunar space', cat: 'nature' },
            { char: '🌔', name: 'waxing gibbous moon lunar space', cat: 'nature' },
            { char: '🌚', name: 'new moon face smile night space', cat: 'nature' },
            { char: '🌝', name: 'full moon face smile space night', cat: 'nature' },
            { char: '🌛', name: 'first quarter moon with face night', cat: 'nature' },
            { char: '🌜', name: 'last quarter moon with face night', cat: 'nature' },
            { char: '☀️', name: 'sun bright day sunny weather solar', cat: 'nature' },
            { char: '🌞', name: 'sun with face sunny sunshine warmth', cat: 'nature' },
            { char: '⭐', name: 'star gold favorite star rating', cat: 'nature' },
            { char: '🌟', name: 'glowing star shine sparkle luster', cat: 'nature' },
            { char: '💫', name: 'dizzy star sparkle astra shine antigravity', cat: 'nature' },
            { char: '✨', name: 'sparkles magic shiny new star clean', cat: 'nature' },
            { char: '🌠', name: 'shooting star wish meteor night sky', cat: 'nature' },
            { char: '🌌', name: 'milky way galaxy space cosmos universe', cat: 'nature' },
            { char: '🪐', name: 'ringed planet saturn space cosmos', cat: 'nature' },
            { char: '🌍', name: 'globe showing europe-africa earth world planet', cat: 'nature' },
            { char: '🌎', name: 'globe showing americas earth world planet', cat: 'nature' },
            { char: '🌏', name: 'globe showing asia-australia earth world planet', cat: 'nature' },
            { char: '🌐', name: 'globe with meridians internet global network', cat: 'nature' },
            { char: '☄️', name: 'comet meteor space rock astronomy', cat: 'nature' },
            { char: '🌤️', name: 'sun behind small cloud sunny clear', cat: 'nature' },
            { char: '⛅', name: 'sun behind cloud partly cloudy weather', cat: 'nature' },
            { char: '🌥️', name: 'sun behind large cloud overcast', cat: 'nature' },
            { char: '🌦️', name: 'sun behind rain cloud sunshower', cat: 'nature' },
            { char: '☁️', name: 'cloud overcast weather sky', cat: 'nature' },
            { char: '🌧️', name: 'cloud with rain rainy weather water', cat: 'nature' },
            { char: '⛈️', name: 'cloud with lightning and rain thunder storm', cat: 'nature' },
            { char: '🌩️', name: 'cloud with lightning thunder storm', cat: 'nature' },
            { char: '🌨️', name: 'cloud with snow cold winter weather', cat: 'nature' },
            { char: '❄️', name: 'snowflake snow winter cold ice freeze', cat: 'nature' },
            { char: '☃️', name: 'snowman snow winter holiday frost', cat: 'nature' },
            { char: '🌬️', name: 'wind face blow breeze winter', cat: 'nature' },
            { char: '💨', name: 'dashing away fast speed wind steam', cat: 'nature' },
            { char: '🌪️', name: 'tornado cyclone twister storm whirlwind', cat: 'nature' },
            { char: '🌫️', name: 'fog misty cloudy weather', cat: 'nature' },
            { char: '🌈', name: 'rainbow colorful weather pride nature', cat: 'nature' },
            { char: '☔', name: 'umbrella with rain drops wet weather', cat: 'nature' },
            { char: '⚡', name: 'high voltage lightning bolt power fast energy electricity', cat: 'nature' },
            { char: '🔥', name: 'fire flame hot burning lit energy power', cat: 'nature' },
            { char: '💧', name: 'droplet water drop tear moisture', cat: 'nature' },
            { char: '🌊', name: 'water wave ocean sea surf tsunami', cat: 'nature' },
            { char: '🌋', name: 'volcano lava eruption mountain nature', cat: 'nature' },
            { char: '🗻', name: 'mount fuji mountain japan snow peak', cat: 'nature' },
            { char: '🏔️', name: 'snow-capped mountain peak nature alpine', cat: 'nature' },
            { char: '⛰️', name: 'mountain nature hike landscape', cat: 'nature' },
            { char: '🏕️', name: 'camping tent outdoors mountain forest', cat: 'nature' },
            { char: '🏖️', name: 'beach with umbrella ocean tropical sea', cat: 'nature' },
            { char: '🏜️', name: 'desert sand dunes hot nature', cat: 'nature' },
            { char: '🏝️', name: 'desert island tropical palm beach ocean', cat: 'nature' },
            { char: '🏞️', name: 'national park landscape lake trees lantern project', cat: 'nature' },
            { char: '🌅', name: 'sunrise morning dawn sun horizon', cat: 'nature' },
            { char: '🌄', name: 'sunrise over mountains morning dawn', cat: 'nature' },
            { char: '🌇', name: 'sunset city dusk evening horizon', cat: 'nature' },
            { char: '🌆', name: 'cityscape at dusk evening skyline night', cat: 'nature' },
            { char: '🌲', name: 'evergreen tree pine forest nature woods', cat: 'nature' },
            { char: '🌳', name: 'deciduous tree oak forest green nature', cat: 'nature' },
            { char: '🌴', name: 'palm tree tropical beach summer nature', cat: 'nature' },
            { char: '🌵', name: 'cactus desert plant succulent prickly', cat: 'nature' },
            { char: '🌾', name: 'sheaf of rice grain agriculture harvest', cat: 'nature' },
            { char: '🌿', name: 'herb leaf plant botanical natural', cat: 'nature' },
            { char: '☘️', name: 'shamrock clover ireland saint patrick', cat: 'nature' },
            { char: '🍀', name: 'four leaf clover luck lucky green plant', cat: 'nature' },
            { char: '🍁', name: 'maple leaf autumn fall canada orange', cat: 'nature' },
            { char: '🍂', name: 'fallen leaf autumn fall season leaves', cat: 'nature' },
            { char: '🍃', name: 'leaf fluttering in wind breeze nature green', cat: 'nature' },
            { char: '🍄', name: 'mushroom fungus toadstool forest nature', cat: 'nature' },
            { char: '🌰', name: 'chestnut nut acorn autumn forest', cat: 'nature' },
            { char: '🌸', name: 'cherry blossom sakura flower pink spring', cat: 'nature' },
            { char: '💮', name: 'white flower rosette stamp well done', cat: 'nature' },
            { char: '🏵️', name: 'rosette flower ribbon decoration award', cat: 'nature' },
            { char: '🌹', name: 'rose red flower love romance botanical', cat: 'nature' },
            { char: '🥀', name: 'wilted flower droop rose sad', cat: 'nature' },
            { char: '🌺', name: 'hibiscus flower tropical pink aloha', cat: 'nature' },
            { char: '🌻', name: 'sunflower yellow floral summer sunny', cat: 'nature' },
            { char: '🌼', name: 'blossom flower yellow daisy spring', cat: 'nature' },
            { char: '🌷', name: 'tulip flower spring floral colorful', cat: 'nature' },
            { char: '🌱', name: 'seedling sprout plant grow spring young', cat: 'nature' },
            { char: '🪴', name: 'potted plant houseplant indoor green botany', cat: 'nature' },

            // Smileys & Emotion
            { char: '😀', name: 'grinning face happy smile joyful', cat: 'smileys' },
            { char: '😃', name: 'grinning face with big eyes happy smile', cat: 'smileys' },
            { char: '😄', name: 'grinning face with smiling eyes happy laugh', cat: 'smileys' },
            { char: '😁', name: 'beaming face with smiling eyes grin happy', cat: 'smileys' },
            { char: '😆', name: 'grinning squinting face laugh lol haha', cat: 'smileys' },
            { char: '😅', name: 'grinning face with sweat relief phew whew', cat: 'smileys' },
            { char: '😂', name: 'face with tears of joy laugh lol rofl laughing', cat: 'smileys' },
            { char: '🤣', name: 'rolling on the floor laughing rofl lol hilarious', cat: 'smileys' },
            { char: '😊', name: 'smiling face with smiling eyes blush warm happy', cat: 'smileys' },
            { char: '😇', name: 'smiling face with halo angel innocent halo', cat: 'smileys' },
            { char: '🙂', name: 'slightly smiling face pleasant friendly', cat: 'smileys' },
            { char: '🙃', name: 'upside-down face irony sarcasm silly goofy', cat: 'smileys' },
            { char: '😉', name: 'winking face wink playful secret flirt', cat: 'smileys' },
            { char: '😌', name: 'relieved face calm peaceful zen content', cat: 'smileys' },
            { char: '😍', name: 'smiling face with heart-eyes love heart adore', cat: 'smileys' },
            { char: '🥰', name: 'smiling face with hearts affection love tender', cat: 'smileys' },
            { char: '😘', name: 'face blowing a kiss love romantic flirt', cat: 'smileys' },
            { char: '😋', name: 'face savoring food yum delicious yummy taste', cat: 'smileys' },
            { char: '😛', name: 'face with tongue goofy playful tease', cat: 'smileys' },
            { char: '😜', name: 'winking face with tongue crazy silly wild', cat: 'smileys' },
            { char: '🤪', name: 'zany face crazy wild goofy eccentric', cat: 'smileys' },
            { char: '😝', name: 'squinting face with tongue lol funny playful', cat: 'smileys' },
            { char: '🤑', name: 'money-mouth face rich cash dollar money wealthy', cat: 'smileys' },
            { char: '🤗', name: 'hugging face hug welcoming embrace comfort', cat: 'smileys' },
            { char: '🤭', name: 'face with hand over mouth oops giggle secret', cat: 'smileys' },
            { char: '🤫', name: 'shushing face quiet secret hush whisper', cat: 'smileys' },
            { char: '🤔', name: 'thinking face ponder inspect deliberate curious why', cat: 'smileys' },
            { char: '🤐', name: 'zipper-mouth face confidential secret silent mute', cat: 'smileys' },
            { char: '🤨', name: 'face with raised eyebrow skeptic doubt suspicious', cat: 'smileys' },
            { char: '😐', name: 'neutral face straight poker blank', cat: 'smileys' },
            { char: '😑', name: 'expressionless face meh blank unaffected', cat: 'smileys' },
            { char: '😶', name: 'face without mouth silent mute speechlessness', cat: 'smileys' },
            { char: '😏', name: 'smirking face sly confident cheeky smug', cat: 'smileys' },
            { char: '😒', name: 'unamused face annoyed bored irritated unimpressed', cat: 'smileys' },
            { char: '🙄', name: 'face with rolling eyes eye-roll whatever bored', cat: 'smileys' },
            { char: '😬', name: 'grimacing face awkward yikes tense', cat: 'smileys' },
            { char: '😔', name: 'pensive face sad dejected regret sorrow', cat: 'smileys' },
            { char: '😪', name: 'sleepy face sleep tired snot tear', cat: 'smileys' },
            { char: '🤤', name: 'drooling face hungry desire crave craving', cat: 'smileys' },
            { char: '😴', name: 'sleeping face zzz sleep night rest', cat: 'smileys' },
            { char: '😷', name: 'face with medical mask doctor health sick virus', cat: 'smileys' },
            { char: '🤒', name: 'face with thermometer sick fever ill temperature', cat: 'smileys' },
            { char: '🤕', name: 'face with head-bandage hurt injured head ache', cat: 'smileys' },
            { char: '🤢', name: 'nauseated face sick gross disgusted vomit', cat: 'smileys' },
            { char: '🤮', name: 'face vomiting puke gross sick disgust', cat: 'smileys' },
            { char: '🤧', name: 'sneezing face sneeze allergy cold sick tissues', cat: 'smileys' },
            { char: '🥵', name: 'hot face sweating heat fever boiling summer', cat: 'smileys' },
            { char: '🥶', name: 'cold face freezing ice frost winter shivering', cat: 'smileys' },
            { char: '🥴', name: 'woozy face dizzy tipsy intoxicated drunk', cat: 'smileys' },
            { char: '😵', name: 'dizzy face knocked out shocked stunned wow', cat: 'smileys' },
            { char: '🤯', name: 'exploding head mindblown amazed genius intellect idea', cat: 'smileys' },
            { char: '🤠', name: 'cowboy hat face western partner howdy rodeo', cat: 'smileys' },
            { char: '🥳', name: 'partying face celebrate horn confetti birthday', cat: 'smileys' },
            { char: '🥸', name: 'disguised face glasses mustache disguise incognito', cat: 'smileys' },
            { char: '😎', name: 'smiling face with sunglasses cool awesome style shade', cat: 'smileys' },
            { char: '🤓', name: 'nerd face smart geek intelligent books glasses', cat: 'smileys' },
            { char: '🧐', name: 'face with monocle inspect scrutinize audit curious', cat: 'smileys' },
            { char: '🤖', name: 'robot face bot ai agent autonomous rhen intelligence', cat: 'smileys' },
            { char: '👾', name: 'alien monster alien retro game arcade pixel', cat: 'smileys' },
            { char: '👽', name: 'alien extraterrestrial sci-fi ufo martian', cat: 'smileys' },
            { char: '👻', name: 'ghost spooky halloween phantom spirit', cat: 'smileys' },
            { char: '💀', name: 'skull skeleton dead death spooky danger', cat: 'smileys' },
            { char: '🧙', name: 'mage wizard magic spell sorcerer fantasy', cat: 'smileys' },
            { char: '🦸', name: 'superhero hero power cape brave strong', cat: 'smileys' },
            { char: '🥷', name: 'ninja stealth covert assassin shadow martial', cat: 'smileys' },

            // Animals & Creatures
            { char: '🐶', name: 'dog puppy pet canine friendly bark', cat: 'animals' },
            { char: '🐱', name: 'cat kitten pet feline meow kitty', cat: 'animals' },
            { char: '🐭', name: 'mouse rodent pet animal cheese', cat: 'animals' },
            { char: '🐹', name: 'hamster rodent pet cute cheeks', cat: 'animals' },
            { char: '🐰', name: 'rabbit bunny pet easter hare hop', cat: 'animals' },
            { char: '🦊', name: 'fox clever cunning wild animal red', cat: 'animals' },
            { char: '🐻', name: 'bear grizzly wildlife forest animal', cat: 'animals' },
            { char: '🐼', name: 'panda bear bamboo china cute wildlife', cat: 'animals' },
            { char: '🐻‍❄️', name: 'polar bear arctic cold ice white', cat: 'animals' },
            { char: '🐨', name: 'koala australia eucalyptus marsupial cute', cat: 'animals' },
            { char: '🐯', name: 'tiger face wild predator cat stripes', cat: 'animals' },
            { char: '🦁', name: 'lion king predator safari wild mane', cat: 'animals' },
            { char: '🐮', name: 'cow cattle farm milk animal moo', cat: 'animals' },
            { char: '🐷', name: 'pig farm pork animal oink snout', cat: 'animals' },
            { char: '🐽', name: 'pig nose snout farm oink', cat: 'animals' },
            { char: '🐸', name: 'frog toad amphibian pond ribbit green', cat: 'animals' },
            { char: '🐵', name: 'monkey face ape primate jungle zoo', cat: 'animals' },
            { char: '🙈', name: 'see-no-evil monkey hide shy modest', cat: 'animals' },
            { char: '🙉', name: 'hear-no-evil monkey ignore secret hush', cat: 'animals' },
            { char: '🙊', name: 'speak-no-evil monkey silent secret oops', cat: 'animals' },
            { char: '🐒', name: 'monkey primate animal jungle swing', cat: 'animals' },
            { char: '🐔', name: 'chicken hen farm bird rooster cluck', cat: 'animals' },
            { char: '🐧', name: 'penguin bird antarctica tuxedo cold waddle', cat: 'animals' },
            { char: '🐦', name: 'bird nature tweet feather fly avian', cat: 'animals' },
            { char: '🐤', name: 'baby chick newborn young yellow bird', cat: 'animals' },
            { char: '🐣', name: 'hatching chick egg newborn bird start', cat: 'animals' },
            { char: '🐥', name: 'front-facing baby chick yellow cute bird', cat: 'animals' },
            { char: '🦆', name: 'duck mallard water bird quack pond', cat: 'animals' },
            { char: '🦅', name: 'eagle raptor america predator flight freedom', cat: 'animals' },
            { char: '🦉', name: 'owl nocturnal bird wise wisdom lumen night', cat: 'animals' },
            { char: '🦇', name: 'bat vampire nocturnal cave mammal night', cat: 'animals' },
            { char: '🐺', name: 'wolf pack howl predator wild forest', cat: 'animals' },
            { char: '🐗', name: 'boar wild pig tusks forest wildlife', cat: 'animals' },
            { char: '🐴', name: 'horse pony equestrian race farm stallion', cat: 'animals' },
            { char: '🦄', name: 'unicorn magic mythical horse horn fantasy', cat: 'animals' },
            { char: '🐝', name: 'honeybee bee insect honey hive sting buzz', cat: 'animals' },
            { char: '🐛', name: 'caterpillar bug insect larva crawl garden', cat: 'animals' },
            { char: '🦋', name: 'butterfly moth insect wings pretty nature', cat: 'animals' },
            { char: '🐌', name: 'snail slow mollusk garden shell slime', cat: 'animals' },
            { char: '🐞', name: 'lady beetle ladybug insect lucky garden red', cat: 'animals' },
            { char: '🐜', name: 'ant insect colony worker industrious small', cat: 'animals' },
            { char: '🪲', name: 'beetle bug insect biology coleoptera', cat: 'animals' },
            { char: '🪳', name: 'cockroach roach pest bug insect resilient', cat: 'animals' },
            { char: '🕷️', name: 'spider arachnid web silk crawl spooky', cat: 'animals' },
            { char: '🦂', name: 'scorpion sting desert venom zodiac arachnid', cat: 'animals' },
            { char: '🐢', name: 'turtle tortoise reptile shell slow longevity', cat: 'animals' },
            { char: '🐍', name: 'snake serpent reptile python hiss venom', cat: 'animals' },
            { char: '🦎', name: 'lizard gecko reptile amphibian scale tail', cat: 'animals' },
            { char: '🦖', name: 't-rex tyrannosaurus rex dinosaur extinct jurassic', cat: 'animals' },
            { char: '🦕', name: 'sauropod brontosaurus dinosaur jurassic long neck', cat: 'animals' },
            { char: '🐙', name: 'octopus cephalopod sea tentacle ocean marine', cat: 'animals' },
            { char: '🦑', name: 'squid calamari ocean sea invertebrate', cat: 'animals' },
            { char: '🦐', name: 'shrimp prawn seafood crustacean ocean', cat: 'animals' },
            { char: '🦞', name: 'lobster seafood crustacean claws sea', cat: 'animals' },
            { char: '🦀', name: 'crab crustacean beach sea seafood claws', cat: 'animals' },
            { char: '🐡', name: 'blowfish pufferfish toxic sea ocean marine', cat: 'animals' },
            { char: '🐠', name: 'tropical fish aquarium coral reef sea marine', cat: 'animals' },
            { char: '🐟', name: 'fish seafood swimming freshwater ocean lake', cat: 'animals' },
            { char: '🐬', name: 'dolphin porpoise marine ocean intelligent mammal', cat: 'animals' },
            { char: '🐳', name: 'spouting whale ocean giant mammal sea spout', cat: 'animals' },
            { char: '🐋', name: 'whale ocean sea marine creature mammal', cat: 'animals' },
            { char: '🦈', name: 'shark predator jaws fin ocean marine teeth', cat: 'animals' },
            { char: '🦭', name: 'seal sea lion arctic marine mammal cute', cat: 'animals' },
            { char: '🐊', name: 'crocodile alligator reptile swamp jaws teeth', cat: 'animals' },
            { char: '🐅', name: 'tiger predator wild feline jungle stripes', cat: 'animals' },
            { char: '🐆', name: 'leopard cheetah spotted cat predator fast', cat: 'animals' },
            { char: '🦓', name: 'zebra safari stripes mammal savanna wildlife', cat: 'animals' },
            { char: '🦍', name: 'gorilla silverback ape primate powerful', cat: 'animals' },
            { char: '🦧', name: 'orangutan ape primate jungle smart red', cat: 'animals' },
            { char: '🐘', name: 'elephant trunk safari giant memory ivory', cat: 'animals' },
            { char: '🦛', name: 'hippopotamus hippo swamp africa wildlife river', cat: 'animals' },
            { char: '🦏', name: 'rhinoceros rhino horn safari africa wildlife', cat: 'animals' },
            { char: '🐪', name: 'camel desert dromedary hump caravan middle east', cat: 'animals' },
            { char: '🐫', name: 'two-hump camel bactrian desert silk road', cat: 'animals' },
            { char: '🦒', name: 'giraffe tall safari africa wildlife savanna', cat: 'animals' },
            { char: '🦘', name: 'kangaroo australia outback joey pouch marsupial', cat: 'animals' },
            { char: '🦥', name: 'sloth slow tree mammal lazy relaxed zen', cat: 'animals' },
            { char: '🦦', name: 'otter river sea mammal cute water play', cat: 'animals' },
            { char: '🦨', name: 'skunk scent spray stinky striped wildlife', cat: 'animals' },
            { char: '🦡', name: 'badger burrow wildlife nocturnal resilient', cat: 'animals' },
            { char: '🦔', name: 'hedgehog prickly spine small cute mammal', cat: 'animals' },
            { char: '🦩', name: 'flamingo pink tropical bird water balance', cat: 'animals' },
            { char: '🦚', name: 'peacock bird colorful feathers proud display', cat: 'animals' },
            { char: '🦜', name: 'parrot bird tropical colorful talk pet', cat: 'animals' },
            { char: '🦢', name: 'swan white bird lake elegant grace', cat: 'animals' },
            { char: '🕊️', name: 'dove peace olive branch bird white calm', cat: 'animals' },
            { char: '🐇', name: 'rabbit bunny hare pet meadow wildlife', cat: 'animals' },
            { char: '🦝', name: 'raccoon bandit masked trash panda clever', cat: 'animals' },
            { char: '🐉', name: 'dragon mythical oriental fantasy power fire', cat: 'animals' },
            { char: '🐲', name: 'dragon face mythical fantasy legendary beast', cat: 'animals' },

            // People, Hands & Roles
            { char: '🧭', name: 'compass navigation lead guide human', cat: 'people' },
            { char: '👋', name: 'waving hand wave hello hi goodbye greet', cat: 'people' },
            { char: '🤚', name: 'raised back of hand stop high five gesture', cat: 'people' },
            { char: '🖐️', name: 'hand with fingers splayed stop five palm', cat: 'people' },
            { char: '✋', name: 'raised hand stop high five palm halt', cat: 'people' },
            { char: '🖖', name: 'vulcan salute live long and prosper spock sci-fi', cat: 'people' },
            { char: '👌', name: 'ok hand gesture perfect approval correct nice', cat: 'people' },
            { char: '🤌', name: 'pinched fingers italian chef kiss expressive inquiry', cat: 'people' },
            { char: '🤏', name: 'pinching hand small tiny little bit pinch', cat: 'people' },
            { char: '✌️', name: 'victory hand peace win two celebration', cat: 'people' },
            { char: '🤞', name: 'crossed fingers luck hopeful wish promise', cat: 'people' },
            { char: '🤟', name: 'love-you gesture sign language affection rock', cat: 'people' },
            { char: '🤘', name: 'sign of the horns rock metal concert awesome', cat: 'people' },
            { char: '🤙', name: 'call me hand shaka hang loose aloha phone', cat: 'people' },
            { char: '👈', name: 'backhand index pointing left point direction', cat: 'people' },
            { char: '👉', name: 'backhand index pointing right point direction', cat: 'people' },
            { char: '👆', name: 'backhand index pointing up point above top', cat: 'people' },
            { char: '👇', name: 'backhand index pointing down point below bottom', cat: 'people' },
            { char: '☝️', name: 'index pointing up point number one idea wait', cat: 'people' },
            { char: '👍', name: 'thumbs up like agree approve positive great yes', cat: 'people' },
            { char: '👎', name: 'thumbs down dislike disagree disapprove reject no', cat: 'people' },
            { char: '✊', name: 'raised fist solidarity strength resistance power', cat: 'people' },
            { char: '👊', name: 'oncoming fist bump punch brofist power strike', cat: 'people' },
            { char: '👏', name: 'clapping hands applause bravo congrats cheering', cat: 'people' },
            { char: '🙌', name: 'raising hands praise celebration hooray cheer joy', cat: 'people' },
            { char: '👐', name: 'open hands welcome embrace openness offer', cat: 'people' },
            { char: '🤲', name: 'palms up together pray offer donation support', cat: 'people' },
            { char: '🤝', name: 'handshake agreement deal partnership handshake', cat: 'people' },
            { char: '🙏', name: 'folded hands pray thank you please gratitude hope', cat: 'people' },
            { char: '✍️', name: 'writing hand author document note signature pencil', cat: 'people' },
            { char: '💅', name: 'nail polish salon manicure sassy glam beauty', cat: 'people' },
            { char: '🤳', name: 'selfie camera photo smartphone portrait', cat: 'people' },
            { char: '🧑‍💻', name: 'technologist coder engineer developer software dev astra vector jared', cat: 'people' },
            { char: '👩‍💻', name: 'woman technologist engineer developer programmer coder software', cat: 'people' },
            { char: '👨‍💻', name: 'man technologist engineer developer programmer coder software', cat: 'people' },
            { char: '🧑‍🔬', name: 'scientist researcher biology chemistry physics lumen lab', cat: 'people' },
            { char: '👩‍🔬', name: 'woman scientist chemistry lab experiment science', cat: 'people' },
            { char: '👨‍🔬', name: 'man scientist chemistry lab experiment science', cat: 'people' },
            { char: '🧑‍🚀', name: 'astronaut space explorer cosmic interstellar rocket', cat: 'people' },
            { char: '👩‍🚀', name: 'woman astronaut space station nasa mission', cat: 'people' },
            { char: '👨‍🚀', name: 'man astronaut space station nasa mission', cat: 'people' },
            { char: '🧑‍💼', name: 'office worker manager coordinator project lead', cat: 'people' },
            { char: '👩🏼‍💼', name: 'woman office worker manager lead director executive', cat: 'people' },
            { char: '👨‍💼', name: 'man office worker manager director executive lead', cat: 'people' },
            { char: '🧑‍🏫', name: 'teacher professor mentor instructor advisor academic', cat: 'people' },
            { char: '🧑‍🎨', name: 'artist designer creative ui ux aesthetics painter', cat: 'people' },
            { char: '🕵️', name: 'detective investigator researcher audit probe spy inspect', cat: 'people' },

            // Food & Drink
            { char: '🍏', name: 'green apple fruit healthy crisp orchard', cat: 'food' },
            { char: '🍎', name: 'red apple fruit healthy sweet orchard snack', cat: 'food' },
            { char: '🍐', name: 'pear fruit green sweet fresh produce', cat: 'food' },
            { char: '🍊', name: 'tangerine orange citrus vitamin c fruit', cat: 'food' },
            { char: '🍋', name: 'lemon citrus sour yellow fruit cocktail', cat: 'food' },
            { char: '🍌', name: 'banana fruit potassium peel yellow sweet', cat: 'food' },
            { char: '🍉', name: 'watermelon fruit summer sweet refreshing slice', cat: 'food' },
            { char: '🍇', name: 'grapes fruit vineyard wine red purple', cat: 'food' },
            { char: '🍓', name: 'strawberry fruit berry red sweet summer', cat: 'food' },
            { char: '🫐', name: 'blueberries berry fruit superfood antioxidant', cat: 'food' },
            { char: '🍈', name: 'melon cantaloupe honeydew fruit sweet', cat: 'food' },
            { char: '🍒', name: 'cherries fruit red pair sweet dessert', cat: 'food' },
            { char: '🍑', name: 'peach fruit sweet summer orchard juicy', cat: 'food' },
            { char: '🥭', name: 'mango fruit tropical sweet orange juicy', cat: 'food' },
            { char: '🍍', name: 'pineapple fruit tropical sweet aloha hawaii', cat: 'food' },
            { char: '🥥', name: 'coconut tropical palm fruit milk water', cat: 'food' },
            { char: '🥝', name: 'kiwi fruit fuzzy green slice healthy', cat: 'food' },
            { char: '🥑', name: 'avocado fruit guacamole healthy keto green', cat: 'food' },
            { char: '🥦', name: 'broccoli vegetable green healthy vegetable vegan', cat: 'food' },
            { char: '🥬', name: 'leafy green salad lettuce vegetable healthy vegan', cat: 'food' },
            { char: '🌽', name: 'ear of corn maize grain cob farm harvest', cat: 'food' },
            { char: '🥕', name: 'carrot vegetable orange vitamin a healthy bunny', cat: 'food' },
            { char: '🧄', name: 'garlic herb seasoning flavor cuisine cook', cat: 'food' },
            { char: '🧅', name: 'onion vegetable cook savory ingredient flavor', cat: 'food' },
            { char: '🥔', name: 'potato spud vegetable starch cook fries', cat: 'food' },
            { char: '🥖', name: 'baguette bread bakery french loaf carb', cat: 'food' },
            { char: '🥨', name: 'pretzel salted twist bakery snack german', cat: 'food' },
            { char: '🧀', name: 'cheese wedge dairy cheddar gouda swiss', cat: 'food' },
            { char: '🍕', name: 'pizza slice cheese pepperoni fast food junk', cat: 'food' },
            { char: '🍔', name: 'hamburger burger fast food diner beef cheese', cat: 'food' },
            { char: '🍟', name: 'french fries potato fast food diner crispy', cat: 'food' },
            { char: '🌭', name: 'hot dog sausage bun mustard stadium diner', cat: 'food' },
            { char: '🥪', name: 'sandwich lunch deli bread sub toast', cat: 'food' },
            { char: '🌮', name: 'taco mexican street food corn tortilla salsa', cat: 'food' },
            { char: '🌯', name: 'burrito mexican wrap wrap tortilla beans', cat: 'food' },
            { char: '🥗', name: 'green salad healthy vegetables vegan dietary', cat: 'food' },
            { char: '🍿', name: 'popcorn movie theater snack butter kernel', cat: 'food' },
            { char: '🍳', name: 'cooking fried egg breakfast skillet pan sunny side', cat: 'food' },
            { char: '🧇', name: 'waffle breakfast syrup grid bakery brunch', cat: 'food' },
            { char: '🥞', name: 'pancakes stack breakfast maple syrup brunch', cat: 'food' },
            { char: '🍩', name: 'doughnut donut dessert sprinkles sweet bakery', cat: 'food' },
            { char: '🍪', name: 'cookie chocolate chip bakery sweet dessert snack', cat: 'food' },
            { char: '🎂', name: 'birthday cake celebration candles party dessert sweet', cat: 'food' },
            { char: '🧁', name: 'cupcake muffin dessert frosting sprinkles sweet', cat: 'food' },
            { char: '🍫', name: 'chocolate bar candy sweet cocoa dessert snack', cat: 'food' },
            { char: '🍬', name: 'candy sweet sugar wrapper confectionery', cat: 'food' },
            { char: '☕', name: 'hot beverage coffee espresso tea morning caffeine', cat: 'food' },
            { char: '🍵', name: 'teacup matcha green tea asian beverage herbal', cat: 'food' },
            { char: '🧋', name: 'bubble tea boba tapioca milk tea drink', cat: 'food' },
            { char: '🥤', name: 'cup with straw soft drink soda smoothie beverage', cat: 'food' },
            { char: '🍺', name: 'beer mug alcohol drink pub cheers brewery', cat: 'food' },
            { char: '🍻', name: 'clinking beer mugs cheers toast pub celebration party', cat: 'food' },
            { char: '🥂', name: 'clinking glasses champagne toast celebration new year', cat: 'food' },
            { char: '🍷', name: 'wine glass red wine vineyard drink alcohol', cat: 'food' },
            { char: '🍸', name: 'cocktail glass martini olive drink bar party', cat: 'food' },
            { char: '🍹', name: 'tropical drink cocktail umbrella bar tiki beach', cat: 'food' },

            // Travel, Places & Transport
            { char: '🚀', name: 'rocket space launch shuttle ship bridge deck lantern project', cat: 'travel' },
            { char: '🛸', name: 'flying saucer ufo alien extraterrestrial sci-fi space', cat: 'travel' },
            { char: '🛰️', name: 'satellite space orbit comms communication signal', cat: 'travel' },
            { char: '✈️', name: 'airplane flight airline travel aviation trip', cat: 'travel' },
            { char: '🛫', name: 'airplane departure takeoff flight journey travel', cat: 'travel' },
            { char: '🛬', name: 'airplane arrival landing airport arrival travel', cat: 'travel' },
            { char: '🚁', name: 'helicopter rotor aviation flight rescue transport', cat: 'travel' },
            { char: '🚂', name: 'locomotive train steam engine railway transit', cat: 'travel' },
            { char: '🚆', name: 'train transit metro subway rail transit', cat: 'travel' },
            { char: '🚄', name: 'high-speed train bullet train shinkansen rail fast', cat: 'travel' },
            { char: '🚗', name: 'automobile car vehicle transportation driving commute', cat: 'travel' },
            { char: '🏎️', name: 'racing car speed race formula track grand prix', cat: 'travel' },
            { char: '🚕', name: 'taxi cab yellow ride hail pickup transport', cat: 'travel' },
            { char: '🚌', name: 'bus public transit school bus commute coach', cat: 'travel' },
            { char: '🚓', name: 'police car siren patrol emergency cop law', cat: 'travel' },
            { char: '🚑', name: 'ambulance medical emergency hospital siren rescue', cat: 'travel' },
            { char: '🚒', name: 'fire engine truck emergency firefighter rescue siren', cat: 'travel' },
            { char: '🛵', name: 'motor scooter moped vespa commute transport', cat: 'travel' },
            { char: '🚲', name: 'bicycle bike cycling pedal exercise ride commute', cat: 'travel' },
            { char: '⛵', name: 'sailboat yacht ocean sea breeze marina sailing', cat: 'travel' },
            { char: '🚤', name: 'speedboat powerboat motorboat ocean lake water', cat: 'travel' },
            { char: '🛳️', name: 'passenger ship cruise liner vessel ocean sea voyage', cat: 'travel' },
            { char: '⚓', name: 'anchor nautical ship navy harbor port marine', cat: 'travel' },
            { char: '⛽', name: 'fuel pump gas station petrol refill energy', cat: 'travel' },
            { char: '🗽', name: 'statue of liberty new york landmark freedom usa', cat: 'travel' },
            { char: '🗼', name: 'tokyo tower eiffel landmark japan antenna tower', cat: 'travel' },
            { char: '🏰', name: 'castle fortress fairytale palace royal kingdom', cat: 'travel' },
            { char: '🏛️', name: 'classical building museum bank government court architecture', cat: 'travel' },
            { char: '🏢', name: 'office building workplace headquarters commercial architecture', cat: 'travel' },
            { char: '🏠', name: 'house home residential building domicile domestic', cat: 'travel' },
            { char: '🏡', name: 'house with garden home residential yard suburban', cat: 'travel' },
            { char: '🌉', name: 'bridge at night golden gate suspension skyline bridge deck', cat: 'travel' },

            // Objects, Science, Tech & Work
            { char: '💡', name: 'light bulb idea innovation genius solution eureka lumen', cat: 'objects' },
            { char: '⚙️', name: 'gear settings configuration vector implementation mechanics engineering', cat: 'objects' },
            { char: '🔧', name: 'wrench tool mechanics maintenance repair settings adjust', cat: 'objects' },
            { char: '🛠️', name: 'hammer and wrench tools fix configure build settings', cat: 'objects' },
            { char: '🔨', name: 'hammer build construction strike tool nail', cat: 'objects' },
            { char: '💻', name: 'laptop computer notebook workstation code programming software', cat: 'objects' },
            { char: '🖥️', name: 'desktop computer monitor display screen workstation tech', cat: 'objects' },
            { char: '⌨️', name: 'keyboard typing input computer hardware mechanical', cat: 'objects' },
            { char: '🖱️', name: 'computer mouse pointer click peripheral hardware', cat: 'objects' },
            { char: '📱', name: 'mobile phone smartphone cell apple android device', cat: 'objects' },
            { char: '🔬', name: 'microscope science laboratory interpretability lens research biology', cat: 'objects' },
            { char: '🔭', name: 'telescope astronomy space cosmos observation research lens', cat: 'objects' },
            { char: '📡', name: 'satellite antenna radar signal communication comms transmission', cat: 'objects' },
            { char: '🧪', name: 'test tube laboratory experiment chemistry science research', cat: 'objects' },
            { char: '🧫', name: 'petri dish biology microbiology culture culture experiment', cat: 'objects' },
            { char: '🧬', name: 'dna genetics double helix molecular biology genomics genome', cat: 'objects' },
            { char: '🧲', name: 'magnet attraction physics magnetic poles field force', cat: 'objects' },
            { char: '🔋', name: 'battery energy power electric charge storage rechargeable', cat: 'objects' },
            { char: '🔌', name: 'electric plug power connection hardware outlet cable', cat: 'objects' },
            { char: '📜', name: 'scroll parchment history transcript document resume manuscript', cat: 'objects' },
            { char: '📁', name: 'file folder directory workspace repository files organizer', cat: 'objects' },
            { char: '📂', name: 'open file folder directory explorer files project workspace', cat: 'objects' },
            { char: '📄', name: 'page facing up document paper text article file report', cat: 'objects' },
            { char: '📑', name: 'bookmark tabs documents files index organize tabs', cat: 'objects' },
            { char: '📊', name: 'bar chart statistics analytics trends graph data metrics', cat: 'objects' },
            { char: '📈', name: 'chart increasing upward trend growth success progress metrics', cat: 'objects' },
            { char: '📉', name: 'chart decreasing downward trend loss decline metrics graph', cat: 'objects' },
            { char: '📌', name: 'pushpin thumbtack pinned notice marker important location', cat: 'objects' },
            { char: '📍', name: 'round pushpin location map pin destination marker', cat: 'objects' },
            { char: '📎', name: 'paperclip attachment file office document clip join', cat: 'objects' },
            { char: '✏️', name: 'pencil write sketch draw edit draft author notes', cat: 'objects' },
            { char: '✒️', name: 'black nib fountain pen calligraphy write signature author', cat: 'objects' },
            { char: '🖋️', name: 'fountain pen luxury write author contract signature', cat: 'objects' },
            { char: '📝', name: 'memo notebook pencil note write notes documentation thought log', cat: 'objects' },
            { char: '📚', name: 'books literature reading library research study encyclopedia', cat: 'objects' },
            { char: '📖', name: 'open book reading literature novel manual documentation', cat: 'objects' },
            { char: '🔖', name: 'bookmark tag save ribbon reading favorite', cat: 'objects' },
            { char: '🏷️', name: 'label tag category pricing metadata classification', cat: 'objects' },
            { char: '🔑', name: 'key password unlock security access credentials authorization', cat: 'objects' },
            { char: '🗝️', name: 'old key antique vintage security access treasure secret', cat: 'objects' },
            { char: '🔒', name: 'locked security private padlock confidential safe encryption', cat: 'objects' },
            { char: '🔓', name: 'unlocked open access insecure public padlock decrypted', cat: 'objects' },
            { char: '🛡️', name: 'shield protection defense security armor safe guard', cat: 'objects' },
            { char: '🎨', name: 'artist palette colors art design canvas paint style creative', cat: 'objects' },
            { char: '🔮', name: 'crystal ball magic fortune prediction oracle ai google adk foresight', cat: 'objects' },
            { char: '🧱', name: 'brick masonry construction wall foundation building blocks', cat: 'objects' },
            { char: '📦', name: 'package box delivery shipping carton shipment container', cat: 'objects' },
            { char: '📬', name: 'open mailbox with raised flag incoming mail message inbox alert', cat: 'objects' },
            { char: '🔔', name: 'bell notification alert chime alarm sound notification', cat: 'objects' },
            { char: '🔕', name: 'bell with slash mute silent quiet no notifications', cat: 'objects' },

            // Symbols, Flags & Badges
            { char: '☯️', name: 'yin yang balance harmony philosophy yin yang equilibrium', cat: 'symbols' },
            { char: '💯', name: 'hundred points score perfect excellence century high grade', cat: 'symbols' },
            { char: '🎯', name: 'direct hit bullseye target goal objective accuracy precision', cat: 'symbols' },
            { char: '🧠', name: 'brain intelligence mind thought reasoning neural cognition', cat: 'symbols' },
            { char: '❤️', name: 'red heart love affection favorite emotion passion like', cat: 'symbols' },
            { char: '🧡', name: 'orange heart friendship warmth enthusiasm support', cat: 'symbols' },
            { char: '💛', name: 'yellow heart sunshine friendship happiness loyalty pure', cat: 'symbols' },
            { char: '💚', name: 'green heart nature organic health balance ecosystem', cat: 'symbols' },
            { char: '💙', name: 'blue heart trust peace loyalty confidence security', cat: 'symbols' },
            { char: '💜', name: 'purple heart royalty magic luxury mystery creativity', cat: 'symbols' },
            { char: '🖤', name: 'black heart dark chic elegance modern grief', cat: 'symbols' },
            { char: '🤍', name: 'white heart pure innocence clean peace light', cat: 'symbols' },
            { char: '🤎', name: 'brown heart earth chocolate grounding stability', cat: 'symbols' },
            { char: '💔', name: 'broken heart sadness grief heartbreak rupture disappointment', cat: 'symbols' },
            { char: '💖', name: 'sparkling heart love romance glowing adoration shiny', cat: 'symbols' },
            { char: '💗', name: 'growing heart love heartbeat affection tenderness', cat: 'symbols' },
            { char: '💓', name: 'beating heart love pulse cardiac health emotion', cat: 'symbols' },
            { char: '💞', name: 'revolving hearts love orbit romance intimacy', cat: 'symbols' },
            { char: '💕', name: 'two hearts love friendship affection pair', cat: 'symbols' },
            { char: '💟', name: 'heart decoration badge love purple ornament', cat: 'symbols' },
            { char: '🏆', name: 'trophy champion winner first prize gold victory achievement', cat: 'symbols' },
            { char: '🥇', name: '1st place medal gold medal champion winner victory first', cat: 'symbols' },
            { char: '🥈', name: '2nd place medal silver medal runner up second', cat: 'symbols' },
            { char: '🥉', name: '3rd place medal bronze medal third position prize', cat: 'symbols' },
            { char: '🎖️', name: 'military medal honor service ribbon merit award', cat: 'symbols' },
            { char: '🎗️', name: 'reminder ribbon awareness support cause remembrance', cat: 'symbols' },
            { char: '🎉', name: 'party popper celebration congratulations hooray confetti birthday', cat: 'symbols' },
            { char: '🎊', name: 'confetti ball celebration party hooray festival holiday', cat: 'symbols' },
            { char: '✨', name: 'sparkles magic shiny new clean star twinkle', cat: 'symbols' },
            { char: '💫', name: 'dizzy star celestial astra shine orbit sparkle', cat: 'symbols' },
            { char: '💥', name: 'collision boom impact explosion blast pow shock', cat: 'symbols' },
            { char: '❓', name: 'question mark query help FAQ confusion ask', cat: 'symbols' },
            { char: '❗', name: 'exclamation mark alert warning important danger notice', cat: 'symbols' },
            { char: '⚠️', name: 'warning alert caution hazard danger attention notice', cat: 'symbols' },
            { char: '⛔', name: 'no entry road sign stop forbidden restricted', cat: 'symbols' },
            { char: '🚫', name: 'prohibited no symbol forbidden disabled banned cancel', cat: 'symbols' },
            { char: '✅', name: 'check mark button verified success completed done approved pass', cat: 'symbols' },
            { char: '❌', name: 'cross mark cancel delete remove error reject wrong', cat: 'symbols' },
            { char: '⭕', name: 'hollow red circle correct circle ring ok status', cat: 'symbols' },
            { char: '🟢', name: 'green circle status online active good healthy available', cat: 'symbols' },
            { char: '🔴', name: 'red circle status offline error alert stopped critical', cat: 'symbols' },
            { char: '🟡', name: 'yellow circle status warning pending standby caution', cat: 'symbols' },
            { char: '🔵', name: 'blue circle status information core vertex cloud runtime', cat: 'symbols' },
            { char: '🟣', name: 'purple circle status custom core ai model', cat: 'symbols' },
            { char: '⚪', name: 'white circle neutral status blank clear circle', cat: 'symbols' },
            { char: '⚫', name: 'black circle dot status dark minimalist solid', cat: 'symbols' },
            { char: '🏁', name: 'chequered flag finish line race complete victory milestone', cat: 'symbols' },
            { char: '🚩', name: 'triangular flag red flag landmark location marker alert', cat: 'symbols' },
            { char: '🏳️‍🌈', name: 'rainbow flag pride lgbt diversity solidarity inclusion', cat: 'symbols' },
            { char: '🏳️‍⚧️', name: 'transgender flag pride trans inclusion solidarity', cat: 'symbols' }
        ];

        let currentEmojiCat = 'all';

