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

import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold text-blue-500 mb-4">Home</h2>
      <p className="mb-4">Welcome to Hackathon Judge.</p>
      <Link to="/about" className="text-blue-600 hover:underline">Go to About</Link>
    </div>
  );
}
