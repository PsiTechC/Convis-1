'use client';

import { useMemo, useState } from 'react';

interface CalendarEvent {
  id: string;
  title: string;
  start?: string | null;
  end?: string | null;
  provider: string;
  location?: string | null;
  meeting_link?: string | null;
}

interface MonthlyCalendarProps {
  events: CalendarEvent[];
  isDarkMode: boolean;
  onDateClick?: (date: Date) => void;
  onMonthChange?: (year: number, month: number) => void;
}

const DAYS_OF_WEEK = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

export function MonthlyCalendar({ events, isDarkMode, onDateClick, onMonthChange }: MonthlyCalendarProps) {
  const [currentDate, setCurrentDate] = useState(new Date());

  const { year, month } = useMemo(() => ({
    year: currentDate.getFullYear(),
    month: currentDate.getMonth(),
  }), [currentDate]);

  const calendarDays = useMemo(() => {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();

    const days: (Date | null)[] = [];

    // Add empty cells for days before the first day of the month
    for (let i = 0; i < startingDayOfWeek; i++) {
      days.push(null);
    }

    // Add actual days
    for (let day = 1; day <= daysInMonth; day++) {
      days.push(new Date(year, month, day));
    }

    return days;
  }, [year, month]);

  const eventsByDate = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();

    events.forEach((event) => {
      if (!event.start) return;

      try {
        const eventDate = new Date(event.start);
        const dateKey = `${eventDate.getFullYear()}-${eventDate.getMonth()}-${eventDate.getDate()}`;

        if (!map.has(dateKey)) {
          map.set(dateKey, []);
        }
        map.get(dateKey)!.push(event);
      } catch {
        console.error('Invalid event date:', event.start);
      }
    });

    return map;
  }, [events]);

  const getEventsForDate = (date: Date | null): CalendarEvent[] => {
    if (!date) return [];
    const dateKey = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
    return eventsByDate.get(dateKey) || [];
  };

  const isToday = (date: Date | null): boolean => {
    if (!date) return false;
    const today = new Date();
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    );
  };

  const goToPreviousMonth = () => {
    const newDate = new Date(year, month - 1, 1);
    setCurrentDate(newDate);
    onMonthChange?.(newDate.getFullYear(), newDate.getMonth());
  };

  const goToNextMonth = () => {
    const newDate = new Date(year, month + 1, 1);
    setCurrentDate(newDate);
    onMonthChange?.(newDate.getFullYear(), newDate.getMonth());
  };

  const goToToday = () => {
    const newDate = new Date();
    setCurrentDate(newDate);
    onMonthChange?.(newDate.getFullYear(), newDate.getMonth());
  };

  return (
    <div className="w-full">
      {/* Calendar Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-dark'}`}>
          {MONTHS[month]} {year}
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={goToToday}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isDarkMode
                ? 'bg-gray-700 text-white hover:bg-gray-600'
                : 'bg-neutral-light text-dark hover:bg-neutral-mid/20'
            }`}
          >
            Today
          </button>
          <button
            onClick={goToPreviousMonth}
            className={`p-2 rounded-lg transition-colors ${
              isDarkMode
                ? 'text-gray-400 hover:bg-gray-700 hover:text-white'
                : 'text-neutral-mid hover:bg-neutral-light'
            }`}
            aria-label="Previous month"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button
            onClick={goToNextMonth}
            className={`p-2 rounded-lg transition-colors ${
              isDarkMode
                ? 'text-gray-400 hover:bg-gray-700 hover:text-white'
                : 'text-neutral-mid hover:bg-neutral-light'
            }`}
            aria-label="Next month"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>

      {/* Days of Week Header */}
      <div className="grid grid-cols-7 gap-2 mb-2">
        {DAYS_OF_WEEK.map((day) => (
          <div
            key={day}
            className={`text-center text-sm font-semibold py-2 ${
              isDarkMode ? 'text-gray-400' : 'text-neutral-mid'
            }`}
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-2">
        {calendarDays.map((date, index) => {
          const dayEvents = getEventsForDate(date);
          const isCurrentDay = isToday(date);

          return (
            <div
              key={index}
              onClick={() => date && onDateClick?.(date)}
              className={`
                min-h-[140px] rounded-lg border p-2 transition-all cursor-pointer flex flex-col
                ${date ? 'hover:shadow-md' : ''}
                ${
                  isDarkMode
                    ? date
                      ? 'bg-gray-800/50 border-gray-700 hover:bg-gray-800'
                      : 'bg-gray-900/20 border-gray-800'
                    : date
                      ? 'bg-white border-neutral-mid/10 hover:bg-neutral-light'
                      : 'bg-neutral-light/30 border-neutral-mid/5'
                }
                ${isCurrentDay ? (isDarkMode ? 'ring-2 ring-primary' : 'ring-2 ring-primary') : ''}
              `}
            >
              {date && (
                <>
                  <div className="flex items-center justify-between mb-1 flex-shrink-0">
                    <span
                      className={`
                        text-sm font-semibold
                        ${isCurrentDay ? 'text-primary' : isDarkMode ? 'text-white' : 'text-dark'}
                      `}
                    >
                      {date.getDate()}
                    </span>
                  </div>

                  <div className="space-y-1 overflow-y-auto flex-1">
                    {dayEvents.map((event) => {
                      const eventTime = event.start ? new Date(event.start).toLocaleTimeString('en-US', {
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true,
                      }) : '';

                      return (
                        <div
                          key={event.id}
                          className={`
                            text-[11px] px-2 py-1 rounded-md
                            ${event.provider === 'google'
                              ? isDarkMode
                                ? 'bg-red-900/40 text-red-100 border-l-2 border-red-500'
                                : 'bg-red-100 text-red-800 border-l-2 border-red-500'
                              : isDarkMode
                                ? 'bg-blue-900/40 text-blue-100 border-l-2 border-blue-500'
                                : 'bg-blue-100 text-blue-800 border-l-2 border-blue-500'
                            }
                          `}
                          title={`${eventTime} - ${event.title}`}
                        >
                          <div className="font-medium truncate leading-tight">{event.title}</div>
                          {eventTime && (
                            <div className={`text-[10px] mt-0.5 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                              {eventTime}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
