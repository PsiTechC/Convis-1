'use client';

import { useState } from 'react';
import Link from 'next/link';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';

export default function WhatsAppComingSoonPage() {
  const [email, setEmail] = useState('');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [error, setError] = useState('');

  const handleNotifyMe = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('Email is required');
      return;
    }

    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address');
      return;
    }

    // For now, just show success message
    // In future, you can integrate with your notification system
    setIsSubscribed(true);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 via-white to-blue-50 p-4">
      <div className="max-w-4xl w-full">
        <div className="bg-white rounded-3xl shadow-2xl overflow-hidden">
          <div className="p-8 lg:p-16 text-center">

            {/* WhatsApp Icon/Animation */}
            <div className="mb-8 flex justify-center">
              <div className="relative">
                <div className="w-32 h-32 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center shadow-2xl">
                  <svg
                    className="w-20 h-20 text-white"
                    fill="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                  </svg>
                </div>
                {/* Decorative circles */}
                <div className="absolute -top-2 -right-2 w-8 h-8 bg-green-200 rounded-full animate-pulse"></div>
                <div className="absolute -bottom-2 -left-2 w-6 h-6 bg-blue-200 rounded-full animate-pulse delay-75"></div>
              </div>
            </div>

            {/* Title */}
            <h1 className="text-4xl lg:text-6xl font-bold text-neutral-dark mb-4 font-heading">
              WhatsApp Integration
            </h1>

            {/* Subtitle */}
            <div className="inline-block bg-gradient-to-r from-green-500 to-green-600 text-white px-6 py-2 rounded-full text-sm font-semibold mb-6 shadow-lg">
              Coming Soon
            </div>

            {/* Description */}
            <p className="text-lg lg:text-xl text-neutral-mid max-w-2xl mx-auto mb-8 leading-relaxed">
              We're working on bringing powerful WhatsApp integration to Convis AI. Soon you'll be able to manage automated conversations, send messages, and engage with your customers directly through WhatsApp.
            </p>

            {/* Features Preview */}
            <div className="grid md:grid-cols-3 gap-6 max-w-3xl mx-auto mb-12">
              <div className="bg-gradient-to-br from-green-50 to-white p-6 rounded-2xl border border-green-100">
                <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-neutral-dark mb-2">Automated Messages</h3>
                <p className="text-sm text-neutral-mid">Send automated WhatsApp messages to your contacts</p>
              </div>

              <div className="bg-gradient-to-br from-blue-50 to-white p-6 rounded-2xl border border-blue-100">
                <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-neutral-dark mb-2">Analytics & Insights</h3>
                <p className="text-sm text-neutral-mid">Track message delivery and engagement metrics</p>
              </div>

              <div className="bg-gradient-to-br from-purple-50 to-white p-6 rounded-2xl border border-purple-100">
                <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                  </svg>
                </div>
                <h3 className="font-semibold text-neutral-dark mb-2">AI Integration</h3>
                <p className="text-sm text-neutral-mid">Connect your AI assistants to WhatsApp conversations</p>
              </div>
            </div>

            {/* Notify Me Form */}
            {!isSubscribed ? (
              <div className="max-w-md mx-auto mb-8">
                <p className="text-neutral-dark font-medium mb-4">
                  Get notified when WhatsApp integration is available
                </p>
                <form onSubmit={handleNotifyMe} className="space-y-3">
                  <div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        setError('');
                      }}
                      placeholder="Enter your email"
                      className={`w-full px-4 py-3 rounded-xl border ${
                        error
                          ? 'border-red-300 focus:border-red-500 focus:ring-2 focus:ring-red-100'
                          : 'border-neutral-mid/20 focus:border-green-500 focus:ring-2 focus:ring-green-100'
                      } focus:outline-none bg-white transition-all duration-200 text-neutral-dark placeholder:text-neutral-mid/50`}
                    />
                    {error && (
                      <p className="mt-1.5 text-xs text-red-600 text-left">{error}</p>
                    )}
                  </div>
                  <button
                    type="submit"
                    className="w-full bg-gradient-to-r from-green-500 to-green-600 text-white py-3.5 px-6 rounded-xl font-semibold hover:shadow-xl hover:shadow-green-500/20 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 shadow-lg transition-all duration-200"
                  >
                    Notify Me
                  </button>
                </form>
              </div>
            ) : (
              <div className="max-w-md mx-auto mb-8 p-6 bg-gradient-to-r from-green-50 to-green-50/50 border border-green-200 rounded-2xl">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <svg className="w-6 h-6 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <p className="text-green-700 font-semibold">You're on the list!</p>
                </div>
                <p className="text-sm text-green-600">
                  We'll notify you as soon as WhatsApp integration is ready.
                </p>
              </div>
            )}

            {/* Back to Dashboard */}
            <div className="pt-6 border-t border-neutral-mid/10">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 text-primary hover:text-primary/80 transition-colors font-medium"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Dashboard
              </Link>
            </div>

            {/* Footer info */}
            <div className="mt-8 pt-6 border-t border-neutral-mid/10">
              <p className="text-sm text-neutral-mid">
                Have questions or suggestions?{' '}
                <a href="mailto:support@convis.ai" className="text-primary hover:text-primary/80 transition-colors font-medium">
                  Contact us
                </a>
              </p>
            </div>
          </div>
        </div>

        {/* Decorative elements */}
        <div className="absolute top-10 left-10 w-20 h-20 bg-green-200 rounded-full blur-3xl opacity-50 -z-10"></div>
        <div className="absolute bottom-10 right-10 w-32 h-32 bg-blue-200 rounded-full blur-3xl opacity-50 -z-10"></div>
      </div>
    </div>
  );
}
