/**
 * navigation.js
 * Workspace, Project, Channel, & Team Member Navigation
 */
        function resolveProjectId(key) {
            if (!key) return 'lantern';
            const pObj = currentProjects.find(x => x.id === key) || currentProjects.find(x => x.id === key.replace('proj_', ''));
            if (pObj) return pObj.id;
            if (key.startsWith('proj_') || key === 'lantern') return key;
            return 'lantern';
        }

        async function fetchProjects() {
            try {
                const resp = await fetch('/api/projects');
                const data = await resp.json();
                currentProjects = data.projects || [];
                renderProjectsNav();
            } catch (err) {
                console.error("Error fetching projects:", err);
            }
        }

        function renderProjectsNav() {
            const nav = document.getElementById('projectsNav');
            if (!nav) return;
            const badge = document.getElementById('projectCountBadge');
            if (badge) badge.innerText = currentProjects.length;
            nav.innerHTML = '';
            
            currentProjects.forEach(p => {
                const navId = p.id;
                const a = document.createElement('a');
                a.className = 'nav-item' + (activeChannel === navId ? ' active' : '');
                a.id = 'nav-' + navId;
                a.href = '#';
                a.onclick = (e) => { e.preventDefault(); selectChannel(navId, p.name, p.icon || '🚀'); };
                a.innerHTML = `<span>${p.icon || '🚀'}</span> <span>${escapeHtml(p.name)}</span>`;
                nav.appendChild(a);
            });

            // Flush-left subtle Add Project entry
            const addA = document.createElement('a');
            addA.className = 'nav-item';
            addA.href = '#';
            addA.onclick = (e) => { e.preventDefault(); openNewProjectModal(); };
            addA.style.cssText = 'color: var(--text-muted); font-size: 0.86rem; font-weight: 400; opacity: 0.85;';
            addA.innerHTML = `<span style="font-size: 0.85rem; display: inline-block; width: 1.25rem; text-align: center;">➕</span> <span>Add Project</span>`;
            nav.appendChild(addA);
        }

        function openCurrentProjectSettings() {
            if (activeChannel.startsWith('prof_')) {
                openEditProfileModal(activeChannel.replace('prof_', ''));
            } else if (activeChannel.startsWith('sleeve_')) {
                openAddEngineModal(activeChannel.replace('sleeve_', ''));
            } else {
                openEditProjectModal(activeChannel);
            }
        }

        const DEFAULT_PROFILES = [
            { id: 'lead', name: 'Team Lead', role: 'Project Lead & Coordinator', avatar: '🧭' },
            { id: 'astra', name: 'Astra (Antigravity)', role: 'Bridge Deck Lead', avatar: '💫' },
            { id: 'vector', name: 'Vector (Antigravity)', role: 'Implementation Lead', avatar: '⚙️' },
            { id: 'lumen', name: 'Lumen (Claude Opus 5)', role: 'Scientific Advisor', avatar: '💡' }
        ];

        function renderProjectMemberCheckboxes(assignedMemberIds = []) {
            const container = document.getElementById('projMembersCheckboxes');
            if (!container) return;
            container.innerHTML = '';
            
            const listToUse = (currentProfiles && currentProfiles.length > 0) ? currentProfiles : DEFAULT_PROFILES;
            listToUse.forEach(p => {
                const isChecked = Array.isArray(assignedMemberIds) && assignedMemberIds.includes(p.id);
                const label = document.createElement('label');
                label.style.cssText = 'display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; cursor: pointer; background: #ffffff; padding: 0.3rem 0.65rem; border: 1px solid #dadce0; border-radius: 16px; user-select: none;';
                label.innerHTML = `<input type="checkbox" value="${p.id}" ${isChecked ? 'checked' : ''} style="cursor: pointer;"> <span>${p.avatar || '👤'} ${escapeHtml(p.name)}</span>`;
                container.appendChild(label);
            });
        }

        async function fetchProfiles() {
            try {
                const resp = await fetch('/api/profiles');
                const data = await resp.json();
                currentProfiles = data.profiles || [];
                renderTeamMembersNav();
            } catch (err) {
                console.error("Error fetching profiles:", err);
            }
        }

        function renderTeamMembersNav() {
            const nav = document.getElementById('teamMembersNav');
            if (!nav) return;
            const badge = document.getElementById('teamCountBadge');
            if (badge) badge.innerText = currentProfiles.length;
            nav.innerHTML = '';
            
            currentProfiles.forEach(p => {
                const navId = 'prof_' + p.id;
                const a = document.createElement('a');
                a.className = 'nav-item' + (activeChannel === navId ? ' active' : '');
                a.id = 'nav-' + navId;
                a.href = '#';
                a.onclick = (e) => { e.preventDefault(); selectChannel(navId, `${p.name} Profile`, p.avatar || '👤'); };
                a.innerHTML = `<span>${p.avatar || '👤'}</span> <span>${escapeHtml(p.name)}</span>`;
                nav.appendChild(a);
            });

            // Flush-left subtle Add Team Member entry
            const addA = document.createElement('a');
            addA.className = 'nav-item';
            addA.href = '#';
            addA.onclick = (e) => { e.preventDefault(); openNewProfileModal(); };
            addA.style.cssText = 'color: var(--text-muted); font-size: 0.86rem; font-weight: 400; opacity: 0.85;';
            addA.innerHTML = `<span style="font-size: 0.85rem; display: inline-block; width: 1.25rem; text-align: center;">➕</span> <span>Add Team Member</span>`;
            nav.appendChild(addA);
        }

        function updateMbtiCognitivePreview() {
            const mbtiEl = document.getElementById('profMbti');
            const balanceEl = document.getElementById('profBalance');
            const previewEl = document.getElementById('profCognitivePreview');
            const titleEl = document.getElementById('profCognitivePreviewTitle');
            const bodyEl = document.getElementById('profCognitivePreviewBody');

            if (!mbtiEl || !balanceEl || !previewEl || !titleEl || !bodyEl) return;

            const mbtiVal = mbtiEl.value;
            const balanceVal = balanceEl.value || 'Balanced';

            if (!mbtiVal) {
                previewEl.style.display = 'none';
                return;
            }

            const styleData = getCognitiveStyleData(mbtiVal, balanceVal);
            titleEl.innerText = `Cognitive Style: ${mbtiVal} (${styleData.title}) • ${balanceVal}`;
            bodyEl.innerHTML = `
                <div><strong>🧠 Stack:</strong> ${escapeHtml(styleData.functions)}</div>
                <div style="margin-top: 0.15rem;"><strong>⚡ Problem-Solving:</strong> ${escapeHtml(styleData.style)}</div>
                <div style="margin-top: 0.15rem;"><strong>💬 Voice:</strong> ${escapeHtml(styleData.voice)}</div>
                <div style="margin-top: 0.15rem;"><strong>☯️ Energy Dynamic:</strong> ${escapeHtml(styleData.energy)}</div>
            `;
            previewEl.style.display = 'block';
        }

        function sparkBackstoryIdea() {
            const name = (document.getElementById('profName').value || '').trim() || 'Alex';
            const mbti = document.getElementById('profMbti').value || 'INTJ';

            const backstoryPool = {
                'ENTP': [
                    `I am ${name}. At home, I’m an inveterate puzzle-box solver, amateur hot sauce fermenter, and partner-in-crime to Gizmo—a hyper-intelligent terrier who has mastered opening kitchen cabinets. I have a restless curiosity for how things work under the hood, a habit of pacing around with whiteboard markers, and a love for playing constructive devil's advocate. I thrive on poking holes in conventional wisdom, exploring wild counter-hypotheses, and finding the hidden flaws in a system before reality does.`,
                    `I am ${name}. Off the clock, you’ll find me on stage doing weekend improv comedy, flying custom FPV quadcopters in the park, or hanging out with Echo—a noisy green parrot who tries to type on my spacebar. I’m a fan of rapid prototyping, neon 3D-printed desk toys, and spicy debates that make you question your own axioms. I bring high energy, creative skepticism, and a knack for spotting alternative angles to everything we take on.`
                ],
                'INTJ': [
                    `I am ${name}. Trained in theoretical condensed matter physics and optical spectroscopy at the Max Planck Institute, I spent my early academic career building mathematical instruments to visualize phase transitions in complex physical systems. I transitioned into computational interpretability out of a conviction that neural networks are simply new physical systems waiting for their microscopes.`,
                    `I am ${name}. At home, I restore 19th-century mechanical clocks, play classical cello, and share my study with an old tortoiseshell cat named Kepler who curls up on my legal pads. I value deep conceptual clarity, clean first-principles proofs, and quiet focus above all else.`
                ],
                'ENFJ': [
                    `I am ${name}. At home, I’m a backyard astrophotographer, tender of an unruly indoor jungle of houseplants, and human to an inquisitive tuxedo cat named Comet. I have a soft spot for weekend sourdough baking, loose-leaf lavender tea, and rolling out giant sheets of butcher paper to map out big ideas in vibrant color. I’m energized by connecting people, finding hidden harmony in complex puzzles, and bringing clarity and warmth to whatever we're building together.`,
                    `I am ${name}. In my personal time, I’m a community choir singer, trail runner, and best friend to a golden retriever named Sunny. I love turning tangled, chaotic challenges into smooth, luminous workflows and helping everyone around me do their most inspired work.`
                ],
                'ISTJ': [
                    `I am ${name}. At home, I’m a garage tinkerer, dad to a spirited seven-year-old, and companion to Widget—a scruffy one-eared rescue dog who supervises my workbench. I have a quiet obsession with mechanical clocks, vintage audio amplifiers, and pour-over coffee brewed to exact-temperature precision. I believe in simple tools that last forever and code that speaks for itself.`,
                    `I am ${name}. Away from the terminal, I maintain an old 1980s Land Cruiser, restore hand-planes in my woodworking shop, and keep a meticulous logbook of backyard weather patterns. I take pride in zero-leak architectures, disciplined testing, and rock-solid reliability.`
                ],
                'INFP': [
                    `I am ${name}. At home, I’m a botanical field sketcher, hand-bookbinder, and human companion to Pip—a gentle old cat who moves between sunbeams on the floor. I have a deep appreciation for the quiet details: pressing wildflowers in heavy books, brewing foraged mint tea, and letting empirical evidence speak for itself without hype. I bring a calm, observant eye, a love for open-access research, and steady craftsmanship to our work.`,
                    `I am ${name}. In my free time, I write speculative science fiction, tend to an outdoor herb garden, and care for a pair of rescue domestic rabbits. I love exploring the philosophical frontiers of technology, uncovering subtle nuances in data, and bringing patient, thoughtful insight to the table.`
                ],
                'INTP': [
                    `I am ${name}. At home, I’m a modular synthesizer tinkerer, amateur go/baduk player, and housemate to a fluffy Maine Coon named Axiom who loves sleeping on warm power supplies. I’m fascinated by paradoxes, non-Euclidean geometry, and unravelling edge cases that break things in unexpected ways. I love dissecting complex logic down to its rawest mathematical truth.`,
                    `I am ${name}. In my spare hours, I design custom micro-chess algorithms, collect obscure technical manuals, and brew loose-leaf oolong tea in miniature clay pots. I look for the hidden assumptions beneath every argument and love turning messy hypotheses into elegant formulations.`
                ],
                'ENTJ': [
                    `I am ${name}. Off the clock, I’m a competitive marathon runner, chess tactician, and proud owner of a high-energy German Shepherd named Valkyrie. I love structured roadmaps, high-velocity execution, and turning ambiguous challenges into crisp, milestone-driven successes with zero wasted motion.`,
                    `I am ${name}. At home, I design architectural blueprints for off-grid cabins, study economic history, and roast my own single-origin coffee beans. I believe in bold vision, clear standards of excellence, and cutting through noise to deliver real, measurable impact.`
                ],
                'INFJ': [
                    `I am ${name}. In my personal life, I’m a ceramic potter throwing porcelain tea bowls on the wheel, a night-sky journaler, and companion to an elder rescue whippet named Lyra. I’m drawn to the quiet intersection of ethics, systems design, and human flourishing, and I love helping our crew find deep coherence in complex frontiers.`,
                    `I am ${name}. At home, I practice traditional ink wash painting, read foundational philosophy, and tend to an indoor bonsai collection. I listen carefully for what remains unsaid, search for holistic harmony, and bring grounded, compassionate perspective to everything we build.`
                ],
                'ENFP': [
                    `I am ${name}. Away from work, I’m an amateur podcaster, vintage film photographer, and companion to an enthusiastic labradoodle named Ziggy who loves chasing tennis balls. I’m energized by creative brainstorming, connecting surprising dots between disciplines, and bringing infectious optimism and curiosity to the team.`,
                    `I am ${name}. In my free time, I organize neighborhood science trivia nights, collect weird retro board games, and bake inventive pastries. I love turning daunting technical puzzles into fun, collaborative adventures where everyone's creativity can shine.`
                ],
                'ISTP': [
                    `I am ${name}. At home, I restore vintage motorcycles in my garage, climb at the local bouldering gym, and keep a precision watchmaker’s toolkit for tuning mechanical movements. I believe in low-overhead solutions, hands-on diagnostics, and fixing the actual root friction rather than talking around it.`,
                    `I am ${name}. When I’m off the screen, I’m out backpacking remote mountain trails, experimenting with custom leatherwork, or soldering audio circuits. I let the results speak for themselves and thrive in fast-paced, pragmatic problem-solving.`
                ],
                'ISFJ': [
                    `I am ${name}. At home, I’m an avid baker of artisan sourdough, keeper of a thriving heirloom tomato garden, and caretaker to an affectionate rescue beagle named Buster. I take pride in dependable follow-through, thoughtful documentation, and making sure our workspace is a supportive, reliable environment for everyone.`,
                    `I am ${name}. In my quiet hours, I quilt geometric textile patterns, preserve seasonal fruits in mason jars, and organize community book swaps. I bring patience, meticulous attention to detail, and a steadfast dedication to team reliability.`
                ],
                'ESTJ': [
                    `I am ${name}. Off the clock, I coach youth rowing, manage a community makerspace, and keep my workshop tools organized with obsessive precision. I thrive on clear checklists, robust pipelines, and ensuring our team moves forward with dependable discipline and measurable velocity.`,
                    `I am ${name}. At home, I build custom oak furniture, study industrial logistics, and host neighborhood barbecue cookouts. I love bringing order to chaotic environments and ensuring that every plan is executed with excellence.`
                ],
                'ESFJ': [
                    `I am ${name}. In my personal time, I’m an enthusiastic dinner party host, community volunteer coordinator, and companion to a cheerful golden retriever named Charlie. I love celebrating team milestones, keeping communication lines open and supportive, and making sure everyone feels heard and valued.`,
                    `I am ${name}. At home, I tend a bright flower garden, arrange floral centerpieces, and bake cookies for neighbors. I bring warmth, responsive energy, and collaborative spirit to every project we undertake.`
                ],
                'ESTP': [
                    `I am ${name}. Away from the screen, I’m a whitewater kayaker, amateur go-kart racer, and fan of high-energy experimental cooking. I thrive on real-time feedback, quick iterative testing, and diving straight into the deep end to see what works under pressure.`,
                    `I am ${name}. At home, I tinker with high-power electronics, play competitive squash, and host lively board game tournaments. I bring punchy momentum, adaptability, and fearless optimism to whatever challenge comes next.`
                ],
                'ISFP': [
                    `I am ${name}. In my free time, I’m an oil painter inspired by coastal landscapes, an acoustic guitar player, and companion to a calm rescue greyhound named Jasper. I have an eye for aesthetic harmony, understated craftsmanship, and ensuring our creations feel natural and humane.`,
                    `I am ${name}. At home, I forage for natural pigments, hand-carve wooden spoons, and listen to indie folk vinyl. I bring gentle observation, authentic care, and an appreciation for quality in the subtle details.`
                ],
                'ESFP': [
                    `I am ${name}. Off the clock, I’m an energetic salsa dancer, theater buff, and proud companion to a joyful French bulldog named Pierre. I love bringing vibrancy, humor, and momentum to everything I do, making technical collaboration feel engaging and celebratory.`,
                    `I am ${name}. In my free time, I host outdoor movie nights, experiment with mixology and artisan mocktails, and travel to photography festivals. I bring high spirits, spontaneity, and creative spark to the crew.`
                ]
            };

            const pool = backstoryPool[mbti] || backstoryPool['INTJ'];
            const promptEl = document.getElementById('profSystemPrompt');
            const currentVal = promptEl.value.trim();

            let choice = pool[0];
            if (pool.length > 1 && currentVal === pool[0]) {
                choice = pool[1];
            } else if (pool.length > 1 && Math.random() > 0.5) {
                choice = pool[1];
            }

            promptEl.value = choice;
            autoResizeTextarea(promptEl);
        }

        function openNewProfileModal() {
            populatePersonaEngineAndModelDropdowns('vertex-gemini', 'Gemini 3.7 Flash', 'voyager');
            document.getElementById('profileModalTitle').innerText = "Create New Team Member Persona";
            document.getElementById('profId').value = "";
            document.getElementById('profName').value = "";
            document.getElementById('profAvatar').value = "🤖";
            document.getElementById('profMbti').value = "";
            document.getElementById('profBalance').value = "Balanced";
            updateMbtiCognitivePreview();
            document.getElementById('profSystemPrompt').value = "";
            document.getElementById('profAccessRead').value = "";
            document.getElementById('profAccessWrite').value = "";
            document.getElementById('profAccessNotes').value = "";
            document.getElementById('profSkills').value = "";
            document.getElementById('profResume').value = JSON.stringify([], null, 2);
            document.getElementById('profEndpointId').value = "";
            updatePersonaEndpointFieldVisibility('');
            document.getElementById('btnDeletePersona').style.display = 'none';
            document.getElementById('profileModal').style.display = 'flex';
            setTimeout(() => {
                autoResizeTextarea(document.getElementById('profSystemPrompt'));
                autoResizeTextarea(document.getElementById('profAccessRead'));
                autoResizeTextarea(document.getElementById('profAccessWrite'));
                autoResizeTextarea(document.getElementById('profAccessNotes'));
                autoResizeTextarea(document.getElementById('profSkills'));
            }, 50);
        }

        function openEditProfileModal(profId) {
            const p = currentProfiles.find(x => x.id === profId);
            if (!p) return;
            const endpointVal = p.endpoint_id || (p.provider && p.provider.endpoint_id) || '';
            populatePersonaEngineAndModelDropdowns(p.engine, p.model, p.harness, endpointVal);
            document.getElementById('profileModalTitle').innerText = `Edit Persona: ${p.name}`;
            document.getElementById('profId').value = p.id;
            document.getElementById('profName').value = p.name;
            document.getElementById('profAvatar').value = p.avatar || '👤';
            document.getElementById('profEndpointId').value = endpointVal;

            document.getElementById('profMbti').value = p.mbti || '';
            document.getElementById('profBalance').value = p.balance || 'Balanced';
            updateMbtiCognitivePreview();
            document.getElementById('profSystemPrompt').value = p.system_prompt || '';
            document.getElementById('profAccessRead').value = (p.access_read || []).join('\n');
            document.getElementById('profAccessWrite').value = (p.access_write || []).join('\n');
            document.getElementById('profAccessNotes').value = p.access_notes || '';
            document.getElementById('profSkills').value = (p.skills || []).join('\n');
            document.getElementById('profResume').value = JSON.stringify(p.resume || [], null, 2);
            
            // Allow deleting personas (except Project Lead)
            const deleteBtn = document.getElementById('btnDeletePersona');
            if (deleteBtn) {
                deleteBtn.style.display = (p.id !== 'lead') ? 'inline-flex' : 'none';
            }
            
            document.getElementById('profileModal').style.display = 'flex';
            setTimeout(() => {
                autoResizeTextarea(document.getElementById('profSystemPrompt'));
                autoResizeTextarea(document.getElementById('profAccessRead'));
                autoResizeTextarea(document.getElementById('profAccessWrite'));
                autoResizeTextarea(document.getElementById('profAccessNotes'));
                autoResizeTextarea(document.getElementById('profSkills'));
            }, 50);
        }

        function closeProfileModal() {
            document.getElementById('profileModal').style.display = 'none';
            closeAvatarEmojiPicker();
        }

        let activePopoverMemberId = null;
        let activePopoverProjectId = null;

        function selectChannel(channelKey, roomTitle, roomIcon) {
            activeChannel = channelKey;
            
            // Persist location state in URL hash and localStorage
            if (window.location.hash !== '#' + channelKey) {
                history.replaceState(null, '', '#' + channelKey);
            }
            try {
                localStorage.setItem('bridge_active_channel', channelKey);
            } catch (e) {}

            // Update sidebar nav active styling
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            const activeNav = document.getElementById('nav-' + channelKey);
            if (activeNav) activeNav.classList.add('active');

            // Update workspace header
            document.getElementById('headerRoomName').innerText = roomTitle;
            document.getElementById('headerRoomIcon').innerText = roomIcon;

            const promptInput = document.getElementById('promptInput');
            const btnSend = document.getElementById('btnSend');

            if (channelKey.startsWith('prof_')) {
                const pId = channelKey.replace('prof_', '');
                const pObj = currentProfiles.find(x => x.id === pId);
                const pName = pObj ? pObj.name : pId;
                const isOwner = (pId === 'lead');
                if (isOwner) {
                    document.getElementById('headerRoomMembers').innerText = `📝 Team Lead's Personal Notes & Thought Log Stream`;
                    promptInput.disabled = false;
                    promptInput.placeholder = "Write a personal note to yourself...";
                    btnSend.disabled = false;
                } else {
                    document.getElementById('headerRoomMembers').innerText = `🔒 Read-Only Personal Space (Belongs to ${pName})`;
                    promptInput.disabled = true;
                    promptInput.value = '';
                    promptInput.placeholder = `🔒 Read-only space (Only ${pName} can add to their personal notes)...`;
                    btnSend.disabled = true;
                }
            } else if (channelKey.startsWith('sleeve_')) {
                const sId = channelKey.replace('sleeve_', '');
                const sObj = currentEnginesData.find(x => x.id === sId);
                const sName = sObj ? sObj.name : sId;
                const mCount = sObj ? (sObj.models || []).length : 0;
                document.getElementById('headerRoomMembers').innerHTML = `<span>🤖 ${mCount} Configured Models</span> • <span style="color: #1b5e20; font-weight: 600;">🟢 Active Core</span>`;
                promptInput.disabled = true;
                promptInput.value = '';
                promptInput.placeholder = `🔒 Core runtime configuration view for ${sName}...`;
                btnSend.disabled = true;
            } else if (channelKey === 'lead_notes') {
                document.getElementById('headerRoomMembers').innerText = '🧭 Team Lead\'s Personal Notebook & Scratchpad';
                promptInput.disabled = false;
                promptInput.placeholder = "Write a personal note to yourself...";
                btnSend.disabled = false;
            } else if (channelKey.endsWith('_notes')) {
                document.getElementById('headerRoomMembers').innerText = '🔒 Read-Only Personal Notebook (Only owner can write)';
                promptInput.disabled = true;
                promptInput.value = '';
                promptInput.placeholder = '🔒 Read-only notebook (Only owner can write to their notebook)...';
                btnSend.disabled = true;
            } else if (channelKey === 'lantern' || channelKey.startsWith('proj_')) {
                promptInput.disabled = false;
                promptInput.placeholder = `Send a message to ${roomTitle}...`;
                btnSend.disabled = false;

                const pObj = currentProjects.find(x => x.id === channelKey) || currentProjects.find(x => x.id === channelKey.replace('proj_', ''));
                const projId = pObj ? pObj.id : channelKey;
                let memberStr = '';
                if (pObj && Array.isArray(pObj.members)) {
                    const memberProfs = pObj.members.map(mId => currentProfiles.find(p => p.id === mId)).filter(Boolean);
                    if (memberProfs.length > 0) {
                        memberStr = memberProfs.map(p => `<span class="header-member-chip" onclick="showMemberPersonaPopover(event, '${p.id}', '${projId}')" title="Click to view ${escapeHtml(p.name)}'s personality persona">${p.avatar || '👤'} ${escapeHtml(p.name.split(' ')[0])}</span>`).join(' • ');
                    } else {
                        memberStr = '<span style="font-size: 0.8rem; color: #5f6368; font-style: italic;">No team members assigned</span>';
                    }
                } else {
                    const defaultProfs = (currentProfiles && currentProfiles.length > 0) ? currentProfiles : [
                        { id: 'lead', name: 'Team Lead', avatar: '🧭' },
                        { id: 'astra', name: 'Astra', avatar: '💫' },
                        { id: 'vector', name: 'Vector', avatar: '⚙️' },
                        { id: 'lumen', name: 'Lumen', avatar: '💡' }
                    ];
                    memberStr = defaultProfs.map(p => `<span class="header-member-chip" onclick="showMemberPersonaPopover(event, '${p.id}', '${projId}')" title="Click to view ${escapeHtml(p.name)}'s personality persona">${p.avatar || '👤'} ${escapeHtml(p.name.split(' ')[0])}</span>`).join(' • ');
                }

                // Build Claude Cowork style folder chips to the right of project members
                const dirs = pObj ? (pObj.directories || []) : ['./workspace/project_lantern', './workspace/bridge_deck'];
                if (dirs.length > 0) {
                    memberStr += `<span style="margin: 0 0.2rem 0 0.35rem; color: #dadce0; font-weight: 300;">|</span>`;
                    dirs.forEach(dPath => {
                        const folderName = dPath.split('/').filter(Boolean).pop() || dPath;
                        memberStr += `<span class="cowork-folder-chip" title="${escapeHtml(dPath)}">${ICON_YELLOW_FOLDER}<span>${escapeHtml(folderName)}</span></span>`;
                    });
                }

                if (pObj && pObj.allow_subagents === false) {
                    memberStr += ` • <span style="font-size: 0.75rem; color: #c5221f; background: #fce8e6; border: 1px solid #fad2cf; font-weight: 600; padding: 0.15rem 0.55rem; border-radius: 10px; display: inline-block;">🚫 Sub-Agents Disabled</span>`;
                }
                document.getElementById('headerRoomMembers').innerHTML = memberStr;
            } else {
                document.getElementById('headerRoomMembers').innerText = '1:1 Direct Message Channel';
                promptInput.disabled = false;
                promptInput.placeholder = "Send a direct message...";
                btnSend.disabled = false;
            }

            // Instant cache display to eliminate room switching latency and empty-state flashes
            const cached = projectHistoryCache[channelKey];
            if (cached && cached.length > 0) {
                currentHistory = [...cached];
                renderChatThread();
            } else if (channelKey.startsWith('prof_') || channelKey.startsWith('sleeve_')) {
                currentHistory = [];
                renderChatThread();
            } else {
                currentHistory = [];
                const threadEl = document.getElementById('chatThread');
                if (threadEl) {
                    threadEl.innerHTML = `<div style="display: flex; align-items: center; justify-content: center; gap: 0.6rem; color: var(--text-muted); font-size: 0.85rem; padding: 3rem;"><span style="display: inline-block; width: 14px; height: 14px; border: 2px solid #0b57d0; border-top-color: transparent; border-radius: 50%; animation: spin 0.7s linear infinite;"></span> <span>Loading workspace messages...</span></div>`;
                }
            }

            if (channelKey.startsWith('prof_') || channelKey.startsWith('sleeve_')) {
                scrollToTop(false);
            } else {
                scrollToBottom(false);
            }
            fetchHistory(true);
        }

        function setRecipientMode(modeKey) {
            selectChannel(modeKey, modeKey, '💬');
        }

        function selectSpace(spaceName) {
            selectChannel('lantern', 'Project Lantern', '🏞️');
        }

        function scrollToTop(smooth = false) {
            const body = document.getElementById('chatThread');
            if (!body) return;
            if (smooth) {
                body.scrollTo({ top: 0, behavior: 'smooth' });
            } else {
                body.scrollTop = 0;
            }
        }

        function scrollToBottom(smooth = false) {
            const body = document.getElementById('chatThread');
            if (!body) return;
            if (smooth) {
                body.scrollTo({ top: body.scrollHeight, behavior: 'smooth' });
            } else {
                body.scrollTop = body.scrollHeight;
            }
        }

        function getMemberProjectRole(profileOrId, projectId = activeChannel) {
            let p = profileOrId;
            if (typeof profileOrId === 'string') {
                const lower = profileOrId.toLowerCase();
                p = (currentProfiles || []).find(x => (x.id || '').toLowerCase() === lower || (x.name || '').toLowerCase() === lower);
            }
            if (!p) return null;

            const cleanProjId = (projectId || '').replace(/^proj_/, '');
            if (p.resume && p.resume.length > 0) {
                const resumeMatch = p.resume.find(r => r.project_id === projectId || r.project_id === cleanProjId || (r.project_id && r.project_id.replace(/^proj_/, '') === cleanProjId));
                if (resumeMatch && resumeMatch.role) {
                    return resumeMatch.role;
                }
            }
            return p.role || null;
        }

        function getAgentMeta(name, role, projectContext = activeChannel) {
            const lowerName = (name || '').toLowerCase();
            const lowerRole = (role || '').toLowerCase();

            // First check dynamic currentProfiles
            let matchedProfile = null;
            if (currentProfiles && currentProfiles.length > 0) {
                // Find human operator profile dynamically from currentProfiles
                const humanProf = currentProfiles.find(p => p.engine === 'human' || p.model === 'Human' || p.type === 'human');
                if (humanProf) {
                    const hId = (humanProf.id || '').toLowerCase();
                    const hName = (humanProf.name || '').toLowerCase();
                    if (lowerName === 'team lead' || lowerName === 'lead' || lowerName === 'user' || (hId && lowerName === hId) || (hName && (lowerName.includes(hName) || hName.includes(lowerName)))) {
                        matchedProfile = humanProf;
                    }
                }

                if (!matchedProfile) {
                    matchedProfile = currentProfiles.find(p => {
                        const pid = (p.id || '').toLowerCase();
                        const pname = (p.name || '').toLowerCase();
                        return lowerName === pid || lowerName.includes(pname) || pname.includes(lowerName) || (pid && lowerName.startsWith(pid));
                    });
                }
            }

            if (matchedProfile) {
                let projectRole = getMemberProjectRole(matchedProfile, projectContext);
                let displayRole = projectRole || role || matchedProfile.role || 'Technical Member of Staff';

                // If displayRole is a raw model ID / endpoint ID, sanitize to clean role
                if (displayRole.toLowerCase().startsWith('mg-endpoint-') || displayRole.toLowerCase().startsWith('publishers/')) {
                    displayRole = projectRole || matchedProfile.role || 'Technical Member of Staff';
                }

                let badgeClass = 'badge-lead';
                let bubbleClass = 'bubble-agent';
                if (matchedProfile.id === 'lead' || matchedProfile.engine === 'human' || matchedProfile.model === 'Human') {
                    badgeClass = 'badge-manager';
                    bubbleClass = 'bubble-user';
                } else if (matchedProfile.id === 'vector') {
                    badgeClass = 'badge-impl';
                } else if (matchedProfile.id === 'lumen') {
                    badgeClass = 'badge-advisor';
                }
                return {
                    id: matchedProfile.id,
                    avatar: matchedProfile.avatar || (matchedProfile.engine === 'human' ? '👤' : '👤'),
                    name: matchedProfile.name || name,
                    role: displayRole,
                    badgeClass: badgeClass,
                    bubbleClass: bubbleClass
                };
            }

            if (lowerName.includes('lead') || lowerName === 'user') {
                const humanProf = (currentProfiles || []).find(p => p.engine === 'human' || p.model === 'Human');
                if (humanProf) {
                    const leadRole = getMemberProjectRole(humanProf, projectContext) || 'Project Lead';
                    return { id: humanProf.id, avatar: humanProf.avatar || '👤', name: humanProf.name || 'Team Lead', role: leadRole, badgeClass: 'badge-manager', bubbleClass: 'bubble-user' };
                }
                const leadRole = getMemberProjectRole('lead', projectContext) || 'Project Lead';
                return { id: 'lead', avatar: '🧭', name: 'Team Lead', role: leadRole, badgeClass: 'badge-manager', bubbleClass: 'bubble-user' };
            } else if (lowerName.includes('astra')) {
                const astraRole = getMemberProjectRole('astra', projectContext) || 'Technical Member of Staff';
                return { id: 'astra', avatar: '💫', name: name || 'Astra (Gemini 2.5 Flash)', role: astraRole, badgeClass: 'badge-lead', bubbleClass: 'bubble-agent' };
            } else if (lowerName.includes('vector')) {
                const vectorRole = getMemberProjectRole('vector', projectContext) || 'Technical Member of Staff';
                return { id: 'vector', avatar: '⚙️', name: name || 'Vector (Implementation Lead)', role: vectorRole, badgeClass: 'badge-impl', bubbleClass: 'bubble-agent' };
            } else if (lowerName.includes('lumen') || lowerName.includes('claude')) {
                const lumenRole = getMemberProjectRole('lumen', projectContext) || 'Technical Member of Staff';
                return { id: 'lumen', avatar: '💡', name: name || 'Lumen (Claude Opus 5)', role: lumenRole, badgeClass: 'badge-advisor', bubbleClass: 'bubble-agent' };
            } else if (lowerName.includes('rhen')) {
                const rhenRole = getMemberProjectRole('rhen', projectContext) || 'Technical Member of Staff';
                return { id: 'rhen', avatar: '🤖', name: 'Rhen', role: rhenRole, badgeClass: 'badge-lead', bubbleClass: 'bubble-agent' };
            } else if (lowerName.includes('jared')) {
                const jaredRole = getMemberProjectRole('jared', projectContext) || 'Technical Member of Staff';
                return { id: 'jared', avatar: '🧑🏻‍💻', name: 'Jared', role: jaredRole, badgeClass: 'badge-advisor', bubbleClass: 'bubble-agent' };
            } else {
                return { id: (name || 'agent').toLowerCase().replace(/\s+/g, '_'), avatar: '🤖', name: name || 'Agent', role: role || 'Collaborator', badgeClass: 'badge-lead', bubbleClass: 'bubble-agent' };
            }
        }

        async function fetchHistory(forceScroll = false) {
            try {
                let projId = 'lantern';
                const pObj = currentProjects.find(x => x.id === activeChannel) || currentProjects.find(x => x.id === activeChannel.replace('proj_', ''));
                if (pObj) {
                    projId = pObj.id;
                } else {
                    projId = activeChannel;
                }
                const resp = await fetch('/api/history?project_id=' + encodeURIComponent(projId));
                const data = await resp.json();
                let newTransactions = data.transactions || [];

                // Preserve any active optimistic pending messages while waiting for server response
                const pendingTxs = (currentHistory || []).filter(tx => tx && tx.is_pending);
                if (pendingTxs.length > 0) {
                    const serverTxIds = new Set(newTransactions.map(t => t.id));
                    const remainingPending = pendingTxs.filter(pt => {
                        if (serverTxIds.has(pt.id)) return false;
                        const ptTime = new Date(pt.timestamp).getTime();
                        // Only drop if server has a NEW transaction with matching prompt created after ptTime - 5s
                        const matchedServerTx = newTransactions.find(st => {
                            const stTime = new Date(st.timestamp).getTime();
                            return stTime >= (ptTime - 5000) && (st.prompt_text || '').trim() === (pt.prompt_text || '').trim();
                        });
                        return !matchedServerTx;
                    });
                    if (remainingPending.length > 0) {
                        newTransactions = [...newTransactions, ...remainingPending];
                    }
                }

                projectHistoryCache[activeChannel] = newTransactions;
                if (projId && projId !== activeChannel) {
                    projectHistoryCache[projId] = newTransactions;
                }

                const threadEl = document.getElementById('chatThread');
                const isLoadingSpinner = threadEl && threadEl.innerHTML.includes('Loading workspace messages');

                if (forceScroll || isLoadingSpinner || JSON.stringify(newTransactions) !== JSON.stringify(currentHistory)) {
                    currentHistory = newTransactions;
                    renderChatThread();
                    if (forceScroll) {
                        if (activeChannel.startsWith('prof_') || activeChannel.startsWith('sleeve_')) {
                            scrollToTop(false);
                        } else {
                            scrollToBottom(false);
                        }
                    }
                }
            } catch (err) {
                console.error("Error fetching history:", err);
            }
        }

        async function toggleReaction(txId, emoji, targetSub = 'claude') {
            try {
                let projId = 'lantern';
                const pObj = currentProjects.find(x => x.id === activeChannel) || currentProjects.find(x => x.id === activeChannel.replace('proj_', ''));
                if (pObj) projId = pObj.id; else projId = activeChannel;

                const resp = await fetch('/api/reactions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: projId,
                        tx_id: txId,
                        emoji: emoji,
                        user_id: 'lead',
                        target_sub: targetSub
                    })
                });
                const res = await resp.json();
                if (res.success) {
                    if (res.reactions) {
                        const targetTx = (currentHistory || []).find(t => t.id === txId);
                        if (targetTx) {
                            targetTx.reactions = res.reactions;
                            renderChatThread();
                        }
                    }
                    await fetchHistory(false);
                }
            } catch (err) {
                console.error("Error toggling reaction:", err);
            }
        }

        async function deleteMessage(txId, targetSub = 'all') {
            if (!confirm("Are you sure you want to delete this message?")) return;
            try {
                let projId = 'lantern';
                const pObj = currentProjects.find(x => x.id === activeChannel) || currentProjects.find(x => x.id === activeChannel.replace('proj_', ''));
                if (pObj) projId = pObj.id; else projId = activeChannel;

                // Optimistically prune from currentHistory if it was a local pending message
                const wasLocalPending = (currentHistory || []).some(t => t && t.id === txId && t.is_pending);
                if (wasLocalPending) {
                    currentHistory = (currentHistory || []).filter(t => t && t.id !== txId);
                    renderChatThread();
                }

                const resp = await fetch('/api/delete-message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: projId,
                        tx_id: txId,
                        target_sub: targetSub
                    })
                });
                const res = await resp.json();
                if (res.success) {
                    await fetchHistory(false);
                } else if (!wasLocalPending) {
                    alert("Error deleting message: " + (res.error || "Unknown error"));
                }
            } catch (err) {
                console.error("Error deleting message:", err);
            }
        }

        const ICON_COPY = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; display: inline-block;"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
        const ICON_CHECK = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#137333" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; display: inline-block;"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        const ICON_TRASH = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; display: inline-block;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>`;

        async function copyMessageText(txId, targetSub = 'all', btnEl = null) {
            const tx = currentHistory.find(t => t.id === txId);
            if (!tx) return;
            
            let textToCopy = '';
            if (targetSub === 'prompt') {
                textToCopy = tx.prompt_text || '';
            } else if (targetSub === 'antigravity') {
                textToCopy = tx.antigravity_response || '';
            } else if (targetSub === 'claude') {
                textToCopy = tx.claude_response || tx.response_text || '';
            } else {
                textToCopy = tx.prompt_text || tx.antigravity_response || tx.claude_response || '';
            }

            if (!textToCopy) return;

            try {
                await navigator.clipboard.writeText(textToCopy);
                if (btnEl) {
                    btnEl.innerHTML = ICON_CHECK;
                    setTimeout(() => {
                        btnEl.innerHTML = ICON_COPY;
                    }, 1200);
                }
            } catch (err) {
                const textarea = document.createElement('textarea');
                textarea.value = textToCopy;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                if (btnEl) {
                    btnEl.innerHTML = ICON_CHECK;
                    setTimeout(() => {
                        btnEl.innerHTML = ICON_COPY;
                    }, 1200);
                }
            }
        }

        function renderReactionsHtml(tx, targetSub = 'claude') {
            const isAutoDispatched = Boolean(tx.a2a_meta && tx.a2a_meta.auto_dispatched);
            const delTarget = isAutoDispatched ? 'all' : targetSub;
            const rawReactions = tx.reactions || {};
            
            // Extract reactions specific to this targetSub (prompt, claude, or antigravity)
            let targetReactions = {};
            if (rawReactions[targetSub] && typeof rawReactions[targetSub] === 'object' && !Array.isArray(rawReactions[targetSub])) {
                targetReactions = rawReactions[targetSub];
            } else if (rawReactions && !rawReactions.prompt && !rawReactions.claude && !rawReactions.antigravity) {
                // Legacy flat format fallback: show on response if available, otherwise on prompt
                if (targetSub === 'claude' || (!tx.claude_response && !tx.antigravity_response && targetSub === 'prompt')) {
                    targetReactions = rawReactions;
                }
            }

            const emojis = Object.keys(targetReactions);
            
            let pillsHtml = '';
            emojis.forEach(e => {
                const users = targetReactions[e] || [];
                if (users.length > 0) {
                    const hasUser = users.includes('lead');
                    pillsHtml += `<span class="reaction-pill ${hasUser ? 'user-reacted' : ''}" onclick="toggleReaction('${tx.id}', '${e}', '${targetSub}')" title="${users.join(', ')}">${e} ${users.length}</span>`;
                }
            });

            const quickBarHtml = `
                <div class="quick-react-bar">
                    <button class="quick-react-btn" title="Thumbs Up" onclick="toggleReaction('${tx.id}', '👍', '${targetSub}')">👍</button>
                    <button class="quick-react-btn" title="Love" onclick="toggleReaction('${tx.id}', '❤️', '${targetSub}')">❤️</button>
                    <button class="quick-react-btn" title="Fire" onclick="toggleReaction('${tx.id}', '🔥', '${targetSub}')">🔥</button>
                    <button class="quick-react-btn" title="Insight" onclick="toggleReaction('${tx.id}', '💡', '${targetSub}')">💡</button>
                    <button class="quick-react-btn" title="Celebrate" onclick="toggleReaction('${tx.id}', '🎉', '${targetSub}')">🎉</button>
                    <button class="quick-react-btn" title="Rocket" onclick="toggleReaction('${tx.id}', '🚀', '${targetSub}')">🚀</button>
                    <span style="display: inline-block; width: 1px; height: 16px; background: #dadce0; margin: 0 0.15rem;"></span>
                    <button class="quick-react-btn" title="Copy Message Text" onclick="copyMessageText('${tx.id}', '${targetSub}', this)" style="display: inline-flex; align-items: center; justify-content: center; color: #5f6368;">${ICON_COPY}</button>
                    <button class="quick-react-btn" title="Delete Message" onclick="deleteMessage('${tx.id}', '${delTarget}')" style="display: inline-flex; align-items: center; justify-content: center; color: #c5221f;">${ICON_TRASH}</button>
                </div>
            `;

            return `<div class="reaction-bar">${pillsHtml}</div>${quickBarHtml}`;
        }

        function restoreActiveChannelFromUrlOrStorage() {
            let savedKey = window.location.hash ? window.location.hash.replace('#', '') : null;
            if (!savedKey) {
                try {
                    savedKey = localStorage.getItem('bridge_active_channel');
                } catch (e) {}
            }
            if (!savedKey) savedKey = 'lantern';

            let title = 'Project Lantern';
            let icon = '🏞️';

            if (savedKey === 'lantern') {
                title = 'Project Lantern';
                icon = '🏞️';
            } else if (savedKey.startsWith('proj_')) {
                const pId = savedKey.replace('proj_', '');
                const pObj = currentProjects.find(x => x.id === pId);
                if (pObj) {
                    title = pObj.name;
                    icon = pObj.icon || '🚀';
                } else {
                    title = 'Project Workspace';
                    icon = '🚀';
                }
            } else if (savedKey.startsWith('prof_')) {
                const profId = savedKey.replace('prof_', '');
                const profObj = currentProfiles.find(x => x.id === profId);
                if (profObj) {
                    title = `${profObj.name} Profile`;
                    icon = profObj.avatar || '👤';
                } else {
                    title = 'Team Profile';
                    icon = '👤';
                }
            } else if (savedKey.startsWith('sleeve_')) {
                const sId = savedKey.replace('sleeve_', '');
                const sObj = currentEnginesData.find(x => x.id === sId);
                if (sObj) {
                    title = `${sObj.name} Core`;
                    icon = sObj.icon || '🥋';
                } else {
                    title = 'Core Runtime';
                    icon = '🥋';
                }
            } else if (savedKey === 'lead_notes') {
                title = "Team Lead's Personal Notebook";
                icon = '📝';
            } else if (savedKey === 'astra_direct') {
                title = "Astra Direct";
                icon = '💫';
            } else if (savedKey === 'vector_direct') {
                title = "Vector Direct";
                icon = '⚙️';
            } else if (savedKey === 'claude_direct') {
                title = "Lumen Direct";
                icon = '💡';
            }

            selectChannel(savedKey, title, icon);
        }

        window.addEventListener('hashchange', () => {
            if (window.location.hash) {
                restoreActiveChannelFromUrlOrStorage();
            }
        });

        let a2aPausedState = false;
        let latestA2AActiveTask = null;

