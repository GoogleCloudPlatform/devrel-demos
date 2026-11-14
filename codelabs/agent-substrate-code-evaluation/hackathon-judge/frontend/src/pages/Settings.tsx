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

export default function Settings() {
  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-6">Settings</h2>
      <div className="bg-white border border-slate-200 rounded-lg p-6 max-w-2xl">
        <section className="mb-8">
          <h3 className="text-lg font-semibold mb-4 text-slate-900 border-b pb-2">Profile Settings</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
              <input 
                type="text" 
                defaultValue="Judge User"
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 outline-none transition-all"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Email Address</label>
              <input 
                type="email" 
                defaultValue="judge@example.com"
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 outline-none transition-all"
              />
            </div>
          </div>
        </section>

        <section className="mb-8">
          <h3 className="text-lg font-semibold mb-4 text-slate-900 border-b pb-2">Notifications</h3>
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-medium text-slate-800">Email Notifications</p>
              <p className="text-sm text-slate-500">Receive updates about your assigned projects.</p>
            </div>
            <div className="relative inline-flex h-6 w-11 items-center rounded-full bg-slate-200 cursor-pointer">
              <span className="translate-x-1 inline-block h-4 w-4 transform rounded-full bg-white transition" />
            </div>
          </div>
        </section>

        <div className="flex justify-end gap-3 pt-4 border-t">
          <button className="px-4 py-2 border border-slate-300 rounded-md text-slate-700 hover:bg-slate-50 transition-colors">
            Cancel
          </button>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
