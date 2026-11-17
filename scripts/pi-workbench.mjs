// Small PI adapter. No global prompts, request rewriting or permission overrides.
export default function workbench(pi) {
  let lab = false;
  const enabled = () => process.env.WORKBENCH_MODE !== 'coding';
  const notify = (ctx, text) => { if (ctx.hasUI) ctx.ui.notify(text, 'info'); };
  pi.on('session_start', () => { lab = false; });
  pi.registerCommand('lab', {
    description: 'Enable workbench context for this session',
    handler: async (_args, ctx) => { lab = true; notify(ctx, '工作台已开启'); },
  });
  pi.registerCommand('exit-lab', {
    description: 'Disable workbench context for this session',
    handler: async (_args, ctx) => { lab = false; notify(ctx, '工作台已关闭'); },
  });
  pi.on('input', async (event, ctx) => {
    if (!enabled()) return { action: 'continue' };
    const text = event.text.trim();
    if (/^lab\s*[:：]?$/i.test(text)) {
      lab = true; notify(ctx, '工作台已开启'); return { action: 'handled' };
    }
    if (text === '退出实验') {
      lab = false; notify(ctx, '工作台已关闭'); return { action: 'handled' };
    }
    return { action: 'continue' };
  });
  pi.on('before_agent_start', async (event) => {
    if (!enabled()) return;
    const context = lab
      ? `当前独立工作台：${process.env.WORKBENCH_MODE}。根目录：${process.env.WORKBENCH_ROOT}。
样本放 samples，分析产物放 workspace；相对目标路径以当前项目为准。
先读所选技能。Seep 任务先由 softseep 判型；APK/EXE 按所选专用技能执行。
MCP 先发现工具并查参数，再限范围调用。区分工具缺失、宿主配置和模型请求失败。
只报告实际执行得到的结果；配置存在不代表工具、设备或服务验证通过。
IDA 可选组件需要本机许可证与后端，不能因技能存在就报告它可用。`
      : '当前为独立工作台入口，实验上下文尚未开启。需要工作台流程时输入 lab：或 /lab；退出实验或 /exit-lab 关闭。';
    return { systemPrompt: event.systemPrompt + '\n\n' + context };
  });
}
