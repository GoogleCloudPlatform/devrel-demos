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

import Image from 'next/image';
import { Disclosure } from '@headlessui/react'
import { Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline'
import Link from 'next/link';
import SignOutButton from '@/app/components/sign-out-button';
import useFirebaseAuthentication from '@/app/hooks/use-firebase-authentication';
import SignInButton from '@/app/components/sign-in-button';
import { usePathname } from 'next/navigation';
import { mergeClassNames } from '@/app/lib/merge-class-names';

export default function Navbar() {
  const authUser = useFirebaseAuthentication();

  const pathname = usePathname();
  const navigation = [
    { name: 'Home', href: '/' },
    { name: 'About', href: '/about' },
  ].map((route: { name: string, href: string }) => ({
    ...route,
    current: pathname === route.href,
  }));

  return (
    <Disclosure as="nav" className="border">
      {({ open }: { open: Boolean }) => (
        <>
          <div className="mx-auto max-w-7xl px-2 sm:px-6 lg:px-8">
            <div className="relative flex h-16 items-center justify-between">
              <div className="absolute inset-y-0 left-0 flex items-center sm:hidden">
                {/* Mobile menu button*/}
                <Disclosure.Button id="disclosure-button" className="inline-flex items-center justify-center rounded-md p-2 text-gray-400 hover:underline hover:decoration-[var(--google-cloud-blue)] hover:text-black">
                  <span className="sr-only">Open main menu</span>
                  {open ? (
                    <XMarkIcon className="block h-6 w-6" aria-hidden="true" />
                  ) : (
                    <Bars3Icon className="block h-6 w-6" aria-hidden="true" />
                  )}
                </Disclosure.Button>
              </div>
              <div className="flex flex-1 items-center justify-center sm:items-stretch sm:justify-start">
                <div className="flex flex-shrink-0 items-center">
                  <Image
                    src='/google-cloud-logo.svg'
                    alt='Google Cloud Logo'
                    width='80'
                    height='80'
                    className='block h-8 w-auto'
                    priority
                  />
                </div>
                <div className="hidden sm:ml-6 sm:block">
                  <div className="flex space-x-4">
                    {navigation.map((item) => (
                      <Link
                        key={item.name}
                        href={item.href}
                        className={mergeClassNames(
                          item.current ? 'text-black underline' : 'text-gray-700 hover:underline hover:decoration-[var(--google-cloud-blue)] hover:text-black',
                          'rounded-md px-3 py-2 text-base font-medium'
                        )}
                        aria-current={item.current ? 'page' : undefined}
                      >
                        {item.name}
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
              {authUser.uid ? <SignOutButton /> : <SignInButton />}
            </div>
          </div>

          <Disclosure.Panel className="sm:hidden">
            <div className="space-y-1 px-2 pt-2 pb-3">
              {navigation.map((item) => (
                <Disclosure.Button
                  key={item.name}
                  as="a"
                  href={item.href}
                  className={mergeClassNames(
                    item.current ? 'text-black underline' : 'text-gray-700 hover:underline hover:decoration-[var(--google-cloud-blue)] hover:text-black',
                    'block rounded-md px-3 py-2 text-base font-medium'
                  )}
                  aria-current={item.current ? 'page' : undefined}
                >
                  {item.name}
                </Disclosure.Button>
              ))}
            </div>
          </Disclosure.Panel>
        </>
      )}
    </Disclosure>
  )
}