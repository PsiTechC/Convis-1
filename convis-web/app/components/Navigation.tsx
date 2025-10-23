'use client';

import { useMemo } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

export interface NavigationItem {
  name: string;
  icon: JSX.Element;
  href: string;
}

export const NAV_ITEMS: NavigationItem[] = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    ),
  },
  {
    name: 'AI Agent',
    href: '/ai-agent',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
    ),
  },
  {
    name: 'Phone Numbers',
    href: '/phone-numbers',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
    ),
  },
  {
    name: 'Call logs',
    href: '/phone-numbers?tab=calls',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
    ),
  },
  {
    name: 'Campaigns',
    href: '/campaigns',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
    ),
  },
  {
    name: 'Whatsapp',
    href: '/whatsapp',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    ),
  },
  {
    name: 'Connect calendar',
    href: '/connect-calendar',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    ),
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    ),
  },
];

interface NavigationProps {
  isSidebarCollapsed: boolean;
  setIsSidebarCollapsed: (value: boolean) => void;
  isDarkMode: boolean;
}

export function SidebarNavigation({ isSidebarCollapsed, setIsSidebarCollapsed, isDarkMode }: NavigationProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeTab = searchParams?.get('tab');

  const activeItem = useMemo(() => {
    if (!pathname) {
      return '';
    }

    if (pathname.startsWith('/phone-numbers')) {
      return activeTab === 'calls' ? 'Call logs' : 'Phone Numbers';
    }

    if (pathname.startsWith('/campaigns')) {
      return 'Campaigns';
    }

    const matched = NAV_ITEMS.find((nav) => {
      if (nav.href.includes('?')) {
        return pathname === nav.href.split('?')[0];
      }
      return pathname === nav.href;
    });

    return matched?.name ?? '';
  }, [pathname, activeTab]);

  return (
    <aside
      onMouseEnter={() => setIsSidebarCollapsed(false)}
      onMouseLeave={() => setIsSidebarCollapsed(true)}
      className={`fixed left-0 top-0 h-full ${isDarkMode ? 'bg-gray-800' : 'bg-white'} border-r ${isDarkMode ? 'border-gray-700' : 'border-neutral-mid/10'} transition-all duration-300 z-40 ${isSidebarCollapsed ? 'w-20' : 'w-64'} hidden lg:block`}
    >
      <div className="h-16 flex items-center justify-center border-b border-neutral-mid/10">
        <div className={`flex items-center gap-2 transition-all duration-300 ${isSidebarCollapsed ? 'scale-90' : 'scale-100'}`}>
          <div className="w-8 h-8 bg-gradient-to-br from-primary to-primary/80 rounded-lg"></div>
          {!isSidebarCollapsed && (
            <span className={`text-lg font-bold ${isDarkMode ? 'text-white' : 'text-dark'}`}>Convis AI</span>
          )}
        </div>
      </div>

      <nav className="p-4 space-y-2">
        {NAV_ITEMS.map((item) => {
          const isActive = activeItem === item.name;
          return (
            <button
              key={item.name}
              onClick={() => router.push(item.href)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                isActive
                  ? `${isDarkMode ? 'bg-gray-700 text-white' : 'bg-primary/10 text-primary'}`
                  : `${isDarkMode ? 'text-gray-400 hover:bg-gray-700 hover:text-white' : 'text-dark/60 hover:bg-neutral-light hover:text-dark'}`
              }`}
            >
              <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {item.icon}
              </svg>
              {!isSidebarCollapsed && <span className="font-medium">{item.name}</span>}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
