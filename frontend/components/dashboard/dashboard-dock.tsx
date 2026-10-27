'use client';

import Link from 'next/link';
import { HomeIcon, Inbox, Network, Users, Vault } from 'lucide-react';

import { Dock, DockIcon, DockItem, DockLabel } from '@/components/ui/dock';

const data = [
  {
    title: 'Home',
    href: '/dashboard',
    icon: (
      <HomeIcon className='h-full w-full text-neutral-600 dark:text-neutral-300' />
    ),
  },
  {
    title: 'Nuclear Family',
    href: '/dashboard/nuclear-family',
    icon: (
      <Users className='h-full w-full text-neutral-600 dark:text-neutral-300' />
    ),
  },
  {
    title: 'Family Tree',
    href: '/dashboard/family',
    icon: (
      <Network className='h-full w-full text-neutral-600 dark:text-neutral-300' />
    ),
  },
  {
    title: 'Inbox',
    href: '/dashboard/inbox',
    icon: (
      <Inbox className='h-full w-full text-neutral-600 dark:text-neutral-300' />
    ),
  },
  {
    title: 'Vault',
    href: '/dashboard/vault',
    icon: (
      <Vault className='h-full w-full text-neutral-600 dark:text-neutral-300' />
    ),
  },
];

export function DashboardDock() {
  return (
    <Dock className='items-end pb-3'>
      {data.map((item) => (
        <DockItem
          key={item.title}
          className='aspect-square rounded-full bg-gray-200 dark:bg-neutral-800'
        >
          <DockLabel>{item.title}</DockLabel>
          <DockIcon>
            <Link
              href={item.href}
              title={item.title}
              className='flex h-full w-full items-center justify-center rounded-full'
            >
              {item.icon}
            </Link>
          </DockIcon>
        </DockItem>
      ))}
    </Dock>
  );
}