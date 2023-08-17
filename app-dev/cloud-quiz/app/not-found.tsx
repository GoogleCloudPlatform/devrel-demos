/**
 * Copyright 2023 Google LLC
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

"use client"

import { usePathname } from 'next/navigation';
import Navbar from "@/app/components/navbar";
import ReturnToHomepagePanel from "@/app/components/return-to-homepage-panel";

export default function Home() {
  const pathname = usePathname();

  return (
    <div>
      <Navbar />
      <ReturnToHomepagePanel>
        <div className='py-4'>
          <div>
            <b>404 </b>
            | That&apos;s an error.
          </div>
          <div>
            The requested URL {pathname} was not found on this server.
          </div>
        </div>
      </ReturnToHomepagePanel>
    </div>
  )
}
