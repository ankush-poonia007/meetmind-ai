import { Bot, Cpu } from 'lucide-react';

import { AGENTS_ROSTER_DATA } from '../../data/docsData.js';

export { AGENTS_ROSTER_DATA };

/**
 * AgentTable — Seven Specialized Agents Table (Section 9 Line 742)
 */
function AgentTable() {
  return (
    <div className="agent-table-wrapper" aria-label="Seven specialized agents roster table">
      <table className="agent-table">
        <thead>
          <tr>
            <th scope="col">Agent</th>
            <th scope="col">Responsibility</th>
            <th scope="col">Pattern</th>
            <th scope="col">Assigned Model</th>
          </tr>
        </thead>
        <tbody>
          {AGENTS_ROSTER_DATA.map((agent) => {
            const isHighReasoning = agent.model.includes('3.6');
            return (
              <tr key={agent.name} className="agent-row">
                <td className="agent-name-cell">
                  <div className="agent-name-wrapper">
                    <span className="agent-icon-badge" aria-hidden="true">
                      <Bot size={15} />
                    </span>
                    <div>
                      <strong className="agent-name">{agent.name} Agent</strong>
                      <span className="agent-role-label">{agent.role}</span>
                    </div>
                  </div>
                </td>
                <td className="agent-resp-cell">
                  {agent.responsibility}
                </td>
                <td className="agent-pattern-cell">
                  <span className="pattern-badge">{agent.pattern}</span>
                </td>
                <td className="agent-model-cell">
                  <span
                    className={`model-badge ${isHighReasoning ? 'model-badge-primary' : 'model-badge-lite'}`}
                  >
                    <Cpu size={12} aria-hidden="true" />
                    {agent.model}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default AgentTable;
