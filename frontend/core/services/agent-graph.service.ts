import { Injectable } from '@angular/core';

export interface AgentNode {
  id: string;
  label: string;
  description: string;
  state: string | null;
  isCurrent: boolean;
}

export interface AgentLink {
  source: string;
  target: string;
  states: string[];
  isActive: boolean;
}

export interface AgentGraph {
  currentState: string;
  currentAgentId: string;
  nodes: AgentNode[];
  links: AgentLink[];
}

@Injectable({ providedIn: 'root' })
export class AgentGraphService {
  async load(): Promise<AgentGraph> {
    const response = await fetch('/api/dashboard/agent-network');

    if (!response.ok) {
      throw new Error(`Failed to load agent graph: ${response.status}`);
    }

    return response.json() as Promise<AgentGraph>;
  }
}
