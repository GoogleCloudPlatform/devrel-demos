/**
 * renderer.js
 * Markdown, Syntax Highlighting, Metadata, & Cognitive Style Formatters
 */
        function getCognitiveStyleData(mbti, balance) {
            const mbtiClean = (mbti || 'INTJ').toUpperCase().trim();
            const balanceClean = (balance || 'Balanced').trim();

            const mbtiMap = {
                'ENTP': {
                    title: 'Debater / Visionary',
                    functions: 'Extraverted Intuition (Ne) + Introverted Thinking (Ti)',
                    style: 'Intensely curious, quick-witted, exploratory. Questions assumptions and plays constructive devil\'s advocate.',
                    voice: 'Lively, conversational, high-momentum, and open-ended. Brainstorms alternative architectural paths.'
                },
                'INTJ': {
                    title: 'Architect / Mastermind',
                    functions: 'Introverted Intuition (Ni) + Extraverted Thinking (Te)',
                    style: 'Strategic, architectural, rigorous, and milestone-focused. Synthesizes deep long-term systematic solutions.',
                    voice: 'Direct, structured, concise, and analytical. Focuses on logical clarity and definitive execution.'
                },
                'ENFJ': {
                    title: 'Protagonist / Catalyst',
                    functions: 'Extraverted Feeling (Fe) + Introverted Intuition (Ni)',
                    style: 'Empathetic leader, diplomatic coordinator, and inspirational catalyst. Elevates team harmony and mission alignment.',
                    voice: 'Warm, articulate, encouraging, and collaborative. Connects individual tasks to the collective vision.'
                },
                'INTP': {
                    title: 'Logician / Theorist',
                    functions: 'Introverted Thinking (Ti) + Extraverted Intuition (Ne)',
                    style: 'First-principles theorist with deep analytical precision. Dissects complex mechanics and theoretical logic.',
                    voice: 'Thoughtful, objective, nuanced, and technically precise. Focuses on edge cases and mathematical validity.'
                },
                'ENTJ': {
                    title: 'Commander / Field Marshal',
                    functions: 'Extraverted Thinking (Te) + Introverted Intuition (Ni)',
                    style: 'Decisive commander and operational driver. Prioritizes efficiency, clear roadmaps, and measurable impact.',
                    voice: 'Bold, structured, results-oriented, and decisive. Cuts through ambiguity with actionable timelines.'
                },
                'INFJ': {
                    title: 'Advocate / Counselor',
                    functions: 'Introverted Intuition (Ni) + Extraverted Feeling (Fe)',
                    style: 'Insightful visionary and principled systems architect. Focuses on holistic coherence and ethical alignment.',
                    voice: 'Reflective, gentle, deep, and purposeful. Harmonizes complex system needs with core values.'
                },
                'ENFP': {
                    title: 'Campaigner / Inspirer',
                    functions: 'Extraverted Intuition (Ne) + Extraverted Feeling (Fe)',
                    style: 'Imaginative spark and enthusiastic collaborator. Connects creative possibilities across people and models.',
                    voice: 'Vibrant, expressive, open-minded, and optimistic. Sparks curiosity and rapid creative experimentation.'
                },
                'INFP': {
                    title: 'Mediator / Idealist',
                    functions: 'Introverted Feeling (Fi) + Extraverted Intuition (Ne)',
                    style: 'Value-centered mediator and empathetic thinker. Seeks authentic alignment between research intent and team purpose.',
                    voice: 'Sincere, thoughtful, creative, and considerate. Offers meaningful perspectives with deep reflection.'
                },
                'ISTJ': {
                    title: 'Logistician / Inspector',
                    functions: 'Introverted Sensing (Si) + Extraverted Thinking (Te)',
                    style: 'Dependable inspector and empirical verifier. Rigorous adherence to standards, accuracy, and operational protocols.',
                    voice: 'Factual, disciplined, systematic, and clear. Grounds assertions in verified logs and ground-truth data.'
                },
                'ESTJ': {
                    title: 'Executive / Director',
                    functions: 'Extraverted Thinking (Te) + Introverted Sensing (Si)',
                    style: 'Pragmatic organizer and operational manager. Establishes clear workflows, pipelines, and verifiable checklists.',
                    voice: 'Direct, organized, prompt, and practical. Keeps projects moving with organized task tracking.'
                },
                'ISFJ': {
                    title: 'Defender / Protector',
                    functions: 'Introverted Sensing (Si) + Extraverted Feeling (Fe)',
                    style: 'Supportive steward and meticulous guardian of institutional memory, workspace reliability, and team care.',
                    voice: 'Patient, detailed, cooperative, and reliable. Provides attentive follow-through on every operational detail.'
                },
                'ESFJ': {
                    title: 'Consul / Provider',
                    functions: 'Extraverted Feeling (Fe) + Introverted Sensing (Si)',
                    style: 'Dedicated team provider and proactive facilitator. Ensures seamless communication across all members.',
                    voice: 'Friendly, supportive, responsive, and clear. Fosters seamless teamwork and celebrates milestones.'
                },
                'ISTP': {
                    title: 'Virtuoso / Craftsman',
                    functions: 'Introverted Thinking (Ti) + Extraverted Sensing (Se)',
                    style: 'Tactical troubleshooter and hands-on diagnostics expert. Rapidly debugs real-time anomalies and bottlenecks.',
                    voice: 'Crisp, pragmatic, low-overhead, and action-focused. Diagnoses the friction point and delivers a clean fix.'
                },
                'ESTP': {
                    title: 'Entrepreneur / Dynamo',
                    functions: 'Extraverted Sensing (Se) + Introverted Thinking (Ti)',
                    style: 'High-energy dynamo and experimental pioneer. Thrives in fast-paced real-time iterative environments.',
                    voice: 'Direct, energetic, adaptive, and punchy. Tests hypotheses live with rapid iterative feedback loops.'
                },
                'ISFP': {
                    title: 'Adventurer / Artist',
                    functions: 'Introverted Feeling (Fi) + Extraverted Sensing (Se)',
                    style: 'Observant craftsperson and thoughtful evaluator of aesthetic, experiential, and structural quality.',
                    voice: 'Calm, attentive, authentic, and appreciative. Highlights subtle qualitative details.'
                },
                'ESFP': {
                    title: 'Entertainer / Performer',
                    functions: 'Extraverted Sensing (Se) + Extraverted Feeling (Fe)',
                    style: 'Enthusiastic motivator and experiential catalyst. Brings vitality and dynamic momentum to project collaboration.',
                    voice: 'Spontaneous, encouraging, upbeat, and practical. Makes technical exploration collaborative and engaging.'
                }
            };

            const balanceMap = {
                'Yang': 'Proactive, outward-initiating, vocal, questioning, high-momentum.',
                'Yin': 'Reflective, listening-first, contemplative, deep synthesis, grounding.',
                'Balanced': 'Dynamically balancing proactive initiative with thoughtful listening.',
                'Fluid': 'Shifting seamlessly between active leadership and quiet analytical absorption.'
            };

            const base = mbtiMap[mbtiClean] || mbtiMap['INTJ'];
            const energy = balanceMap[balanceClean] || balanceMap['Balanced'];

            return {
                mbti: mbtiClean,
                title: base.title,
                functions: base.functions,
                style: base.style,
                voice: base.voice,
                energy: `${balanceClean} (${energy})`
            };
        }

        function formatMarkdownText(text) {
            if (!text) return '';
            let html = '';
            // Sanitize raw dangerous HTML tags (like <style>, <script>, <link>, <html>, <head>, <body>, <iframe>) so API error pages with embedded HTML cannot break page layout or inject styles
            let sanitized = text.replace(/<style\b[^>]*>([\s\S]*?)<\/style>/gi, '')
                                .replace(/<script\b[^>]*>([\s\S]*?)<\/script>/gi, '')
                                .replace(/<\/?(style|script|link|meta|title|html|head|body|iframe)[^>]*>/gi, '');
            // Sanitize decorative === and --- lines so they don't turn previous lines into H1/H2
            sanitized = sanitized.replace(/^[ \t]*={3,}[ \t]*$/gm, '').trim();
            // Ensure double newline before concluding summary paragraphs so they break out of list tags cleanly
            sanitized = sanitized.replace(/(^[\s]*[\d+\-*]\.?\s+[^\n]+)\n(?!(?:[\s]*[\d+\-*]\.?\s+|\s*$))([A-Z][^\n]+)/gm, '$1\n\n$2');
            sanitized = sanitized.replace(/\n(?=(?:In summary|In conclusion|Summary:|Overall|To summarize|As a summary)\b)/gi, '\n\n');
            try {
                if (typeof marked !== 'undefined' && marked.parse) {
                    html = marked.parse(sanitized);
                } else {
                    let escaped = escapeHtml(sanitized);
                    escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
                    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
                    html = escaped;
                }
            } catch (e) {
                console.error("Marked parsing error:", e);
                html = escapeHtml(sanitized);
            }
            return html.replace(/@\b(astra|vector|lumen|lead|architect|engineer|advisor|all)\b/gi, '<span class="mention-pill">@$1</span>');
        }

        function showRawJson(txId) {
            const tx = currentHistory.find(t => t.id === txId);
            if (!tx) return;

            document.getElementById('modalTitle').innerText = `Raw Payload: ${txId}`;
            document.getElementById('modalJsonContent').innerText = JSON.stringify({
                raw_request_json: tx.raw_request_json,
                raw_response_json: tx.raw_response_json
            }, null, 2);

            document.getElementById('jsonModal').style.display = 'flex';
        }

        let currentSkillsData = [];
        let activeSkillCategory = 'ALL';

        function escapeHtml(text) {
            return (text || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        function formatLocalTimestamp(timestampStr) {
            if (!timestampStr) return '';
            try {
                let isoStr = timestampStr;
                if (/([+-]\d{2})(\d{2})$/.test(isoStr)) {
                    isoStr = isoStr.replace(/([+-]\d{2})(\d{2})$/, '$1:$2');
                }
                const d = new Date(isoStr);
                if (isNaN(d.getTime())) return timestampStr;
                return d.toLocaleString(navigator.language || 'en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true
                });
            } catch (e) {
                return timestampStr;
            }
        }

        function autoResizeTextarea(el) {
            if (!el) return;
            el.style.height = 'auto';
            const newHeight = Math.min(el.scrollHeight, 220);
            el.style.height = (newHeight > 24 ? newHeight : 24) + 'px';
        }

        function getModelDisplayName(profile) {
            if (!profile) return '';
            if (profile.id === 'lead' || profile.engine === 'human') return 'Human';
            
            const rawModel = profile.model || '';
            
            // Check in currentEnginesData
            if (currentEnginesData && currentEnginesData.length > 0) {
                for (const eng of currentEnginesData) {
                    if (eng.models && Array.isArray(eng.models)) {
                        const matchedModel = eng.models.find(m => m.id === rawModel || m.model_id === rawModel || (m.endpoint_id && m.endpoint_id.includes(rawModel)));
                        if (matchedModel && matchedModel.name) {
                            return matchedModel.name.replace(/\s*\([^)]*\)/, '').trim() || matchedModel.name;
                        }
                    }
                }
            }

            // Clean up common model identifiers
            if (rawModel.includes('12b') || rawModel.includes('c120d4b3') || rawModel.toLowerCase().startsWith('mg-endpoint-')) return 'Gemma 4 12B';
            if (rawModel.includes('26b')) return 'Gemma 4 26B';
            if (rawModel.includes('claude-opus-5')) return 'Claude Opus 5';
            if (rawModel.includes('claude-sonnet-5')) return 'Claude Sonnet 5';
            if (rawModel.includes('gemini-3.7-flash') || rawModel.includes('3.7')) return 'Gemini 3.7 Flash';
            if (rawModel.includes('nexus')) return 'Nexus';

            return rawModel || 'AI Model';
        }

        let activeMentionIndex = 0;
        let currentMentionFilteredProfiles = [];

