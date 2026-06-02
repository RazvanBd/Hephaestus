import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subscription } from 'rxjs';

import { AgentGraph, AgentGraphService, AgentLink } from '../../core/services/agent-graph.service';
import { WebsocketService } from '../../core/services/websocket.service';

@Component({
  selector: 'app-live-feed',
  template: `
    <div class="mode-switch">
      <button (click)="setMode('feed')" [class.active]="mode === 'feed'">Live feed</button>
      <button (click)="setMode('agents')" [class.active]="mode === 'agents'">Agent links</button>
    </div>

    <ng-container *ngIf="mode === 'feed'; else agentMode">
      <pre>{{ events | json }}</pre>
    </ng-container>

    <ng-template #agentMode>
      <p class="current-state">Current state: {{ agentGraph?.currentState || 'loading...' }}</p>

      <div class="agent-grid" *ngIf="agentGraph as graph; else loadingState">
        <section class="agent-card" *ngFor="let node of graph.nodes" [class.current]="node.isCurrent">
          <header>{{ node.label }}</header>
          <p>{{ node.description }}</p>

          <ul>
            <li *ngFor="let link of outgoingLinks(node.id)" [class.active]="link.isActive">
              → {{ labelFor(link.target) }}
              <span>{{ link.states.join(', ') }}</span>
            </li>
          </ul>
        </section>
      </div>

      <ng-template #loadingState>
        <p>Loading agent network…</p>
      </ng-template>
    </ng-template>
  `,
  styles: [`
    .mode-switch {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }

    .mode-switch button.active {
      font-weight: 700;
    }

    .current-state {
      margin: 0 0 1rem;
      font-weight: 600;
    }

    .agent-grid {
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }

    .agent-card {
      border: 1px solid #d0d7de;
      border-radius: 0.75rem;
      padding: 1rem;
      background: #fff;
    }

    .agent-card.current {
      border-color: #0969da;
      box-shadow: 0 0 0 2px rgba(9, 105, 218, 0.12);
    }

    .agent-card header {
      font-weight: 700;
      margin-bottom: 0.5rem;
    }

    .agent-card ul {
      margin: 0.75rem 0 0;
      padding-left: 1rem;
    }

    .agent-card li {
      margin-bottom: 0.5rem;
      color: #57606a;
    }

    .agent-card li.active {
      color: #0969da;
      font-weight: 600;
    }

    .agent-card span {
      display: block;
      font-size: 0.85rem;
    }
  `]
})
export class LiveFeedComponent implements OnInit, OnDestroy {
  mode: 'feed' | 'agents' = 'feed';
  events: unknown[] = [];
  agentGraph: AgentGraph | null = null;
  private subscription?: Subscription;

  constructor(
    private ws: WebsocketService,
    private agentGraphService: AgentGraphService,
  ) {}

  ngOnInit(): void {
    void this.loadAgentGraph();
    this.subscription = this.ws.events$().subscribe((event) => {
      this.events = [...this.events, event].slice(-25);
      if (this.extractStateTransition(event)) {
        void this.loadAgentGraph();
      }
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  setMode(mode: 'feed' | 'agents'): void {
    this.mode = mode;
    if (mode === 'agents' && !this.agentGraph) {
      void this.loadAgentGraph();
    }
  }

  outgoingLinks(source: string): AgentLink[] {
    return this.agentGraph?.links.filter((link) => link.source === source) ?? [];
  }

  labelFor(target: string): string {
    return this.agentGraph?.nodes.find((node) => node.id === target)?.label ?? target;
  }

  private extractStateTransition(event: unknown): string | null {
    if (!event || typeof event !== 'object' || !('event' in event) || !('payload' in event)) {
      return null;
    }

    const { event: eventType, payload } = event as { event?: unknown; payload?: { new_state?: unknown } };
    if (eventType !== 'StateTransition' || !payload || typeof payload.new_state !== 'string') {
      return null;
    }

    return payload.new_state;
  }

  private async loadAgentGraph(): Promise<void> {
    this.agentGraph = await this.agentGraphService.load();
  }
}
