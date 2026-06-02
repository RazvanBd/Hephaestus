import { Injectable } from '@angular/core';

export type TaskStatus = 'QUEUED' | 'RUNNING' | 'WAITING_APPROVAL' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'PAUSED';
export type RunStatus = 'CREATED' | 'RUNNING' | 'WAITING_APPROVAL' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type RunControlCommand = 'START' | 'PAUSE' | 'RESUME' | 'CANCEL' | 'APPROVE';

export interface HephaestusTask {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  run_ids: string[];
}

export interface HephaestusRun {
  id: string;
  task_id: string;
  status: RunStatus;
  current_state: string;
  attempts: number;
  commit_hash: string | null;
}

@Injectable({ providedIn: 'root' })
export class HephaestusService {
  async listTasks(): Promise<HephaestusTask[]> {
    const response = await fetch('/api/hephaestus/tasks');
    if (!response.ok) {
      throw new Error(`Failed to load tasks: ${response.status}`);
    }
    const payload = await response.json() as { tasks: HephaestusTask[] };
    return payload.tasks;
  }

  async listRuns(): Promise<HephaestusRun[]> {
    const response = await fetch('/api/hephaestus/runs');
    if (!response.ok) {
      throw new Error(`Failed to load runs: ${response.status}`);
    }
    const payload = await response.json() as { runs: HephaestusRun[] };
    return payload.runs;
  }

  async createTask(title: string, description: string): Promise<HephaestusTask> {
    const response = await fetch('/api/hephaestus/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description }),
    });
    if (!response.ok) {
      throw new Error(`Failed to create task: ${response.status}`);
    }
    const payload = await response.json() as { task: HephaestusTask };
    return payload.task;
  }

  async createRun(taskId: string): Promise<HephaestusRun> {
    const response = await fetch('/api/hephaestus/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId }),
    });
    if (!response.ok) {
      throw new Error(`Failed to create run: ${response.status}`);
    }
    const payload = await response.json() as { run: HephaestusRun };
    return payload.run;
  }

  async controlRun(runId: string, command: RunControlCommand): Promise<HephaestusRun> {
    const response = await fetch(`/api/hephaestus/runs/${runId}/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    });
    if (!response.ok) {
      throw new Error(`Failed to control run: ${response.status}`);
    }
    const payload = await response.json() as { run: HephaestusRun };
    return payload.run;
  }
}
