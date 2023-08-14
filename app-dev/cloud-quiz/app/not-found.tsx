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
            | That's an error.
          </div>
          <div>
            The requested URL {pathname} was not found on this server.
          </div>
        </div>
      </ReturnToHomepagePanel>
    </div>
  )
}
