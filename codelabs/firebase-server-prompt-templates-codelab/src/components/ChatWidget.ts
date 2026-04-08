/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { callCustomerSupportModel } from '../firebase';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export class ChatWidget {
    private isOpen = false;
    private container: HTMLElement;
    private messages: { text: string; isUser: boolean }[] = [
        { text: 'Operator connected. How can we assist your mission today?', isUser: false }
    ];

    constructor() {
        this.container = document.createElement('div');
        this.container.id = 'chat-widget-container';
        this.loadState();
        this.renderInitial();
        this.renderMessages();
        this.attachListeners();
    }

    private loadState() {
        const saved = localStorage.getItem('chat_history');
        if (saved) {
            this.messages = JSON.parse(saved);
        }
    }

    private saveState() {
        localStorage.setItem('chat_history', JSON.stringify(this.messages));
    }

    private resetChat() {
        this.messages = [
            { text: 'Operator connected. How can we assist your mission today?', isUser: false }
        ];
        this.saveState();
        this.renderMessages();
        this.scrollToBottom();
    }

    private toggle() {
        this.isOpen = !this.isOpen;
        
        const chatWindow = this.container.querySelector('#chat-window');
        if (chatWindow) {
            if (this.isOpen) {
                chatWindow.classList.remove('hidden');
                chatWindow.classList.add('flex');
            } else {
                chatWindow.classList.remove('flex');
                chatWindow.classList.add('hidden');
            }
        }

        const toggleIcon = this.container.querySelector('#chat-toggle-icon');
        if (toggleIcon) {
            toggleIcon.textContent = this.isOpen ? 'close' : 'support_agent';
        }

        const badge = this.container.querySelector('#chat-unread-badge');
        if (badge) {
            if (this.isOpen) {
                badge.classList.add('hidden');
                badge.classList.remove('flex');
            } else {
                badge.classList.remove('hidden');
                badge.classList.add('flex');
            }
        }

        if (this.isOpen) {
            this.scrollToBottom();
            const input = this.container.querySelector('input');
            if (input) input.focus();
        }
    }

    private async sendMessage() {
        const input = this.container.querySelector('input') as HTMLInputElement;
        const message = input.value.trim();
        if (message) {
            this.messages.push({ text: message, isUser: true });
            input.value = '';

            this.saveState();
            this.renderMessages();
            this.scrollToBottom();

            try {
                // Prepare history excluding the just added message if we want to follow strict "history" semantics,
                // but usually the model expects history + current prompt. 
                // Let's rely on the prompt being passed separately and history being previous context.
                const history = this.messages.slice(0, -1).map(msg => ({
                    role: msg.isUser ? 'user' : 'model',
                    contents: msg.text
                }));

                const urlParams = new URLSearchParams(window.location.search);
                const productId = urlParams.get('product') || undefined;
                const response = await callCustomerSupportModel(message, productId, history);

                this.messages.push({ text: response || 'Communications silent.', isUser: false });
                this.saveState();
            } catch (error) {
                console.error('Error calling support model:', error);
                this.messages.push({ text: 'Comms link unstable. Try again.', isUser: false });
                this.saveState();
            }

            this.renderMessages();
            this.scrollToBottom();
        }
    }

    private scrollToBottom() {
        const messageContainer = this.container.querySelector('#chat-messages');
        if (messageContainer) {
            messageContainer.scrollTop = messageContainer.scrollHeight;
        }
    }

    public mount(target: HTMLElement) {
        target.appendChild(this.container);
    }

    private attachListeners() {
        // Toggle Buttons
        const toggleBtn = this.container.querySelector('#chat-toggle-btn');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggle());
        }

        const closeBtn = this.container.querySelector('#chat-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.toggle());
        }

        const resetBtn = this.container.querySelector('#chat-reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetChat());
        }

        // Send Message Interactions
        const sendBtn = this.container.querySelector('#chat-send-btn');
        const input = this.container.querySelector('input');

        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
        }
    }

    private renderMessages() {
        const messageContainer = this.container.querySelector('#chat-messages');
        if (messageContainer) {
            messageContainer.innerHTML = this.messages.map(msg => `
                <div class="self-${msg.isUser ? 'end' : 'start'} max-w-[80%] ${msg.isUser ? 'bg-terrain-orange' : 'bg-terrain-earth'} text-white p-3 font-condensed text-sm shadow-sm prose prose-invert prose-p:leading-normal prose-sm max-w-none">
                    ${DOMPurify.sanitize(marked.parse(msg.text) as string)}
                </div>
            `).join('');
        }
    }

    private renderInitial() {
        const chatWindowHTML = `
            <div id="chat-window" class="hidden fixed bottom-32 right-8 z-50 w-96 flex-col border-4 border-terrain-earth bg-background-rugged shadow-[12px_12px_0px_0px_rgba(27,79,114,1)]">
                <div class="flex items-center justify-between border-b-4 border-terrain-earth bg-terrain-earth px-4 py-3 text-white">
                    <h3 class="font-display text-lg uppercase tracking-wide">Tactical Support</h3>
                    <div class="flex gap-2">
                        <button id="chat-reset-btn" class="hover:text-terrain-orange" title="New Chat"><span class="material-symbols-outlined">refresh</span></button>
                        <button id="chat-close-btn" class="hover:text-terrain-orange"><span class="material-symbols-outlined">close</span></button>
                    </div>
                </div>
                <div id="chat-messages" class="h-96 overflow-y-auto p-4 flex flex-col gap-3">
                </div>
                <div class="border-t-4 border-terrain-earth p-4 bg-white">
                    <div class="flex gap-2">
                        <input type="text" placeholder="TRANSMIT MESSAGE..." class="w-full bg-gray-100 border-2 border-terrain-earth/20 px-3 py-2 text-xs font-display focus:border-terrain-orange focus:ring-0 placeholder:text-gray-400">
                        <button id="chat-send-btn" class="bg-terrain-orange text-white px-3 hover:bg-terrain-earth transition-colors"><span class="material-symbols-outlined text-lg">send</span></button>
                    </div>
                </div>
            </div>
        `;

        const fabHTML = `
            <button id="chat-toggle-btn" aria-label="Open Tactical Support" class="fixed bottom-8 right-8 z-50 flex h-20 w-20 items-center justify-center rounded-none bg-terrain-orange text-white shadow-[8px_8px_0px_0px_rgba(27,79,114,1)] transition-all hover:-translate-y-2 hover:-translate-x-2 hover:shadow-[12px_12px_0px_0px_rgba(27,79,114,1)]">
                <span id="chat-toggle-icon" class="material-symbols-outlined !text-[40px]">support_agent</span>
                <span id="chat-unread-badge" class="absolute -top-1 -right-1 flex h-6 w-6">
                    <span class="absolute inline-flex h-full w-full animate-ping bg-white opacity-75"></span>
                    <span class="relative inline-flex h-6 w-6 bg-white text-terrain-orange font-display text-[10px] items-center justify-center">1</span>
                </span>
            </button>
        `;

        this.container.innerHTML = chatWindowHTML + fabHTML;
    }
}
