'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button } from '@/components/ui';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-paper-bg flex items-center justify-center p-6">
          <div className="card-paper p-8 max-w-md text-center">
            <div className="text-4xl mb-4">😅</div>
            <h2 className="text-xl font-bold text-ink mb-2">哎呀，出错了</h2>
            <p className="text-muted mb-6">
              这张路书暂时没写出来，可能是服务正在休息，稍后再试一次。
            </p>
            <div className="flex gap-3 justify-center">
              <Button
                variant="secondary"
                onClick={() => window.location.reload()}
              >
                再试一次
              </Button>
              <Button
                variant="ghost"
                onClick={() => window.location.href = '/'}
              >
                回到输入
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}