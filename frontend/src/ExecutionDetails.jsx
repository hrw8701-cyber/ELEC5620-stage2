import React from 'react';
import {useLanguage} from './Language';

// Recorded execution metadata only; no generated reasoning or inferred AI calls.
export function ExecutionDetails({execution}) {
  const t=useLanguage();
  return <details className="execution-details"><summary>{t('查看执行详情')}</summary>
    {!execution?<p>{t('此历史事件未保存接口调用记录，无法确认是否调用 AI。')}</p>:<>
      <p>{t('操作')}: {execution.operation}<br/>{t('请求编号')}: {execution.requestId}</p>
      <ol>{execution.steps.map((step,i)=><li key={i}>
        <strong>{step.agent}</strong> <span className="badge">{t(step.modelCall==='succeeded'?'AI 调用成功':step.modelCall==='failed'?'AI 调用失败': '规则处理 · 未调用 AI')}</span>
        <p>{t(step.summary)}</p>
        <small>{t('执行模式')}: {step.mode}{step.durationMs!=null&&<> · {t('耗时')}: {step.durationMs} ms</>}</small>
        {step.endpoint&&<p>{t('模型')}: {step.model}<br/>{t('接口')}: POST {step.endpoint}</p>}
      </li>)}</ol>
      {!execution.steps.length&&<p>{t('本次为服务端规则处理，无 AI 调用。')}</p>}
    </>}
  </details>;
}
