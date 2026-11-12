import type { ReviewTask } from '../domain/types'
import StatusBadge from './StatusBadge'

export default function ReviewQueue({ tasks, onSelect }: { tasks: ReviewTask[]; onSelect?: (task: ReviewTask) => void }) {
  return <div className="grid">{tasks.map(task => <button className="notice" type="button" key={task.id} onClick={() => onSelect?.(task)}><StatusBadge label={task.priority === 'high' ? '高优先级' : '待处理'} tone={task.priority === 'high' ? 'red' : 'amber'} /><span><strong>{task.title}</strong><br />{task.summary}<br /><small className="muted-cell">负责人：{task.assignee} · {task.updatedAt}</small></span><span className="top-spacer">→</span></button>)}</div>
}
