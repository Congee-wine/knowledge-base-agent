import { Skeleton } from 'antd'

export function ChatHistorySkeleton() {
  return (
    <div className="w-full max-w-[810px] space-y-5 px-8 pt-8 lg:ml-[18%] lg:px-0" aria-label="正在加载历史会话">
      <div className="flex justify-end"><Skeleton.Input active size="small" style={{ height: 38, width: 230 }} /></div>
      <Skeleton.Input active size="small" style={{ height: 38, width: 300 }} />
      <div className="flex justify-end"><Skeleton.Input active size="small" style={{ height: 38, width: 180 }} /></div>
      <Skeleton.Input active size="small" style={{ height: 58, width: 420 }} />
    </div>
  )
}
