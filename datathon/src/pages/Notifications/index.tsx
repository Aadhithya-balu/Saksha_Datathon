import React, { useState } from 'react';
import { Bell, Activity, HeartPulse, Clock, ListTodo } from 'lucide-react';
import NotificationCenter from '../../components/notifications/NotificationCenter';
import ActivityFeed from '../../components/notifications/ActivityFeed';
import SystemHealth from '../../components/notifications/SystemHealth';
import LiveEventTimeline from '../../components/notifications/LiveEventTimeline';

type TabView = 'notifications' | 'activity' | 'health' | 'timeline';

const NotificationsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabView>('notifications');

  const tabs: { id: TabView; label: string; icon: React.ReactNode }[] = [
    { id: 'notifications', label: 'Notification Center', icon: <Bell className="w-4 h-4" /> },
    { id: 'activity', label: 'Activity Feed', icon: <Activity className="w-4 h-4" /> },
    { id: 'health', label: 'System Health', icon: <HeartPulse className="w-4 h-4" /> },
    { id: 'timeline', label: 'Live Timeline', icon: <Clock className="w-4 h-4" /> },
  ];

  return (
    <div className="h-[84vh] flex flex-col gap-4 p-1 md:p-3 select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-white/5 pb-3 shrink-0">
        <div>
          <h2 className="text-md font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Bell className="w-5 h-5 text-[#1E6FD9]" />
            Real-Time Intelligence & Notifications
          </h2>
          <p className="text-[9.5px] font-mono text-[#6A7A96] mt-0.5">
            KARNATAKA POLICE — NOTIFICATION CENTER, ACTIVITY FEED, SYSTEM HEALTH & LIVE EVENT TIMELINE
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border-color shrink-0 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-[9.5px] font-mono font-bold uppercase tracking-wider transition-all cursor-pointer border-b-2 ${
              activeTab === tab.id
                ? 'text-white border-[#1E6FD9] bg-[#1E6FD9]/5'
                : 'text-[#6A7A96] border-transparent hover:text-[#A8B4CC] hover:bg-white/[0.02]'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="max-w-5xl mx-auto">
          {activeTab === 'notifications' && (
            <div className="bg-secondary-bg border border-border-color rounded-xl overflow-hidden">
              <NotificationCenter />
            </div>
          )}

          {activeTab === 'activity' && (
            <div className="bg-secondary-bg border border-border-color rounded-xl p-4">
              <ActivityFeed limit={100} />
            </div>
          )}

          {activeTab === 'health' && (
            <div className="bg-secondary-bg border border-border-color rounded-xl p-4">
              <SystemHealth />
            </div>
          )}

          {activeTab === 'timeline' && (
            <div className="bg-secondary-bg border border-border-color rounded-xl p-4">
              <LiveEventTimeline limit={50} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NotificationsPage;

