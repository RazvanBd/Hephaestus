import { Component, OnDestroy, OnInit } from '@angular/core';
import { Subscription } from 'rxjs';

import { AgentGraph, AgentGraphService, AgentLink } from '../../core/services/agent-graph.service';
import { HephaestusRun, HephaestusService, HephaestusTask, RunControlCommand } from '../../core/services/hephaestus.service';
import { WebsocketService } from '../../core/services/websocket.service';

@Component({
  selector: 'app-live-feed',
  template: `
    <div class="mode-switch">
      <button (click)="setMode('feed')" [class.active]="mode === 'feed'">Live feed</button>
      <button (click)="setMode('agents')" [class.active]="mode === 'agents'">Agent links</button>
      <button (click)="setMode('operator')" [class.active]="mode === 'operator'">Operator</button>
    </div>

    <ng-container *ngIf="mode === 'feed'">
      <pre>{{ events | json }}</pre>
    </ng-container>

    <ng-container *ngIf="mode === 'agents'">
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
    </ng-container>

    <ng-container *ngIf="mode === 'operator'">
      <section class="operator-controls">
        <h3>Task Intake</h3>
        <input [(ngModel)]="taskTitle" placeholder="Task title" />
        <textarea [(ngModel)]="taskDescription" placeholder="Task description"></textarea>
        <button (click)="createTask()">Create Task</button>
      </section>

      <section class="operator-grid">
        <article>
          <h3>Task Queue</h3>
          <ul>
            <li *ngFor="let task of tasks">
              <strong>{{ task.title }}</strong>
              <small>{{ task.status }}</small>
              <button (click)="createRun(task.id)">Create Run</button>
            </li>
          </ul>
        </article>

        <article>
          <h3>Runs</h3>
          <ul>
            <li *ngFor="let run of runs">
              <strong>{{ run.id }}</strong>
              <small>{{ run.status }} / {{ run.current_state }}</small>
              <div class="run-actions">
                <button (click)="controlRun(run.id, 'START')">Start</button>
                <button (click)="controlRun(run.id, 'PAUSE')">Pause</button>
                <button (click)="controlRun(run.id, 'RESUME')">Resume</button>
                <button (click)="controlRun(run.id, 'APPROVE')">Approve</button>
                <button (click)="controlRun(run.id, 'CANCEL')">Cancel</button>
              </div>
            </li>
          </ul>
        </article>
      </section>
    </ng-container>
  `,
  styles: [`
    .mode-switch { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
    .mode-switch button.active { font-weight: 700; }
    .current-state { margin: 0 0 1rem; font-weight: 600; }
    .agent-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
    .agent-card { border: 1px solid #d0d7de; border-radius: 0.75rem; padding: 1rem; background: #fff; }
    .agent-card.current { border-color: #0969da; box-shadow: 0 0 0 2px rgba(9, 105, 218, 0.12); }
    .agent-card header { font-weight: 700; margin-bottom: 0.5rem; }
    .agent-card ul { margin: 0.75rem 0 0; padding-left: 1rem; }
    .agent-card li { margin-bottom: 0.5rem; color: #57606a; }
    .agent-card li.active { color: #0969da; font-weight: 600; }
    .agent-card span { display: block; font-size: 0.85rem; }
    .operator-controls { display: grid; gap: 0.5rem; margin-bottom: 1rem; }
    .operator-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
    .operator-grid ul { list-style: none; padding: 0; display: grid; gap: 0.75rem; }
    .operator-grid li { border: 1px solid #d0d7de; border-radius: 0.5rem; padding: 0.75rem; display: grid; gap: 0.5rem; }
    .run-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  `]
})
export class LiveFeedComponent implements OnInit, OnDestroy {
  mode: 'feed' | 'agents' | 'operator' = 'feed';
  events: unknown[] = [];
  agentGraph: AgentGraph | null = null;
  tasks: HephaestusTask[] = [];
  runs: HephaestusRun[] = [];
  taskTitle = '';
  taskDescription = '';
  private subscription?: Subscription;

  constructor(
    private ws: WebsocketService,
    private agentGraphService: AgentGraphService,
    private hephaestusService: HephaestusService,
  ) {}

  ngOnInit(): void {
    void this.loadAgentGraph();
    void this.refreshOperatorData();
    this.subscription = this.ws.events$().subscribe((event) => {
      this.events = [...this.events, event].slice(-25);
      if (this.extractStateTransition(event)) {
        void this.loadAgentGraph();
      }
      if (this.mode === 'operator') {
        void this.refreshOperatorData();
      }
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  setMode(mode: 'feed' | 'agents' | 'operator'): void {
    this.mode = mode;
    if (mode === 'agents' && !this.agentGraph) {
      void this.loadAgentGraph();
    }
    if (mode === 'operator') {
      void this.refreshOperatorData();
    }
  }

  async createTask(): Promise<void> {
    if (!this.taskTitle.trim()) {
      return;
    }
    await this.hephaestusService.createTask(this.taskTitle.trim(), this.taskDescription.trim());
    this.taskTitle = '';
    this.taskDescription = '';
    await this.refreshOperatorData();
  }

  async createRun(taskId: string): Promise<void> {
    await this.hephaestusService.createRun(taskId);
    await this.refreshOperatorData();
  }

  async controlRun(runId: string, command: RunControlCommand): Promise<void> {
    await this.hephaestusService.controlRun(runId, command);
    await this.refreshOperatorData();
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

  private async refreshOperatorData(): Promise<void> {
    [this.tasks, this.runs] = await Promise.all([
      this.hephaestusService.listTasks(),
      this.hephaestusService.listRuns(),
    ]);
  }
}
