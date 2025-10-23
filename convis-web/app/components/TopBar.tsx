'use client';

import { ReactNode } from 'react';

interface TopBarProps {
  isDarkMode: boolean;
  toggleTheme: () => void;
  onLogout: () => void;
  userInitial: string;
  userLabel?: string;
  onToggleMobileMenu?: () => void;
  searchPlaceholder?: string;
  showSearch?: boolean;
  collapseSearchOnMobile?: boolean;
  leftContent?: ReactNode;
  rightContentBefore?: ReactNode;
  rightContentAfter?: ReactNode;
  showNotifications?: boolean;
}

export function TopBar({
  isDarkMode,
  toggleTheme,
  onLogout,
  userInitial,
  userLabel,
  onToggleMobileMenu,
  searchPlaceholder = 'Search for article, video or document',
  showSearch = true,
  collapseSearchOnMobile = false,
  leftContent,
  rightContentBefore,
  rightContentAfter,
  showNotifications = true,
}: TopBarProps) {
  const searchWrapperClasses = collapseSearchOnMobile
    ? 'hidden sm:block flex-1 max-w-xl'
    : 'flex-1 max-w-xl';

  return (
    <header className={`${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-neutral-mid/10'} border-b sticky top-0 z-30`}>
      <div className="flex items-center justify-between gap-4 px-6 py-4">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {onToggleMobileMenu && (
            <button
              onClick={onToggleMobileMenu}
              className="lg:hidden p-2 rounded-lg hover:bg-neutral-light"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}

          {leftContent && (
            <div className="shrink-0">{leftContent}</div>
          )}

          {showSearch && (
            <div className={searchWrapperClasses}>
              <div className="relative">
                <input
                  type="text"
                  placeholder={searchPlaceholder}
                  className={`w-full pl-10 pr-4 py-2.5 rounded-xl ${isDarkMode ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-neutral-light border-neutral-mid/20 text-neutral-dark'} border focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all`}
                />
                <svg className={`w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {rightContentBefore}

          <button
            onClick={toggleTheme}
            className={`p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
          >
            {isDarkMode ? (
              <svg className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-neutral-mid" fill="currentColor" viewBox="0 0 20 20">
                <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
              </svg>
            )}
          </button>

          {showNotifications && (
            <button className={`p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors relative`}>
              <svg className={`w-5 h-5 ${isDarkMode ? 'text-gray-400' : 'text-neutral-mid'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </button>
          )}

          <button
            onClick={onLogout}
            className={`flex items-center gap-2 p-2 rounded-xl ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-neutral-light'} transition-colors`}
          >
            {userLabel && (
              <span className={`${isDarkMode ? 'text-gray-300' : 'text-dark/70'} text-sm font-medium hidden sm:block`}>
                Hi, {userLabel}
              </span>
            )}
            <div className="w-8 h-8 bg-gradient-to-br from-primary to-primary/80 rounded-full flex items-center justify-center">
              <span className="text-xs font-bold text-white">
                {userInitial}
              </span>
            </div>
          </button>

          {rightContentAfter}
        </div>
      </div>
    </header>
  );
}
