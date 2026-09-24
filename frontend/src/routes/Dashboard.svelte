<script>
  import { onMount } from 'svelte';
  import { link, push } from 'svelte-spa-router';
  import { api } from '../lib/api.js';

  let stats = null;
  let error = '';

  onMount(async () => {
    try {
      stats = await api('/dashboard/stats');
    } catch (e) {
      error = e.message;
    }
  });

  function gotoLots() {
    push('/lots');
  }
</script>

<h1 class="page-title">工艺总览</h1>
<p class="page-sub">按染坊 → 染缸 → 染程 → 色牢度推进；顶部步骤条可跳转各工序。</p>

{#if error}
  <p class="err">{error}</p>
{/if}

{#if stats}
  <div class="grid-stats">
    <div class="stat">
      <div class="n">{stats.dyeHouseTotal}</div>
      <div class="l">染坊</div>
    </div>
    <div class="stat">
      <div class="n">{stats.vatReadyCount}</div>
      <div class="l">就绪染缸</div>
    </div>
    <div class="stat">
      <div class="n">{stats.vatDyeingCount}</div>
      <div class="l">染色中</div>
    </div>
    <div class="stat">
      <div class="n">{stats.lotsLast7d}</div>
      <div class="l">近 7 日染程</div>
    </div>
    <div class="stat">
      <div class="n">{stats.checksLast24h}</div>
      <div class="l">近 24 时抽检</div>
    </div>
    <div
      class="stat"
      class:stat-warn={stats.openRetestUnmetCount > 0}
      role="button"
      tabindex="0"
      title="在染程列表按「未关闭 + 复测未达标」手数，行数与本数一致"
      on:click={gotoLots}
      on:keydown={(e) => e.key === 'Enter' && gotoLots()}
    >
      <div class="n">{stats.openRetestUnmetCount}</div>
      <div class="l">未关闭·复测未达标</div>
    </div>
  </div>
{/if}

<div class="panel">
  <p style="margin:0 0 0.75rem;color:var(--indigo-mist);font-size:0.9rem;">
    业务约束：仅当染缸为 <strong>ready</strong> 或 <strong>dyeing</strong> 时可新建染程；新建后染缸自动变为
    dyeing。排液可用染缸「完成排液」动作。
  </p>
  {#if stats}
    <p style="margin:0 0 0.75rem;color:var(--indigo-mist);font-size:0.9rem;">
      色牢度复测规定次数为 <strong>{stats.requiredRetestCount}</strong>
      次（常量 REQUIRED_RETEST_COUNT，至少 2）。染程下至少一条色牢度复测次数达标才可关闭，否则返回
      409；关闭后禁止再追加色牢度。上方「未关闭·复测未达标」与染程列表同条件筛选手数结果一致。
    </p>
  {/if}
  <div class="toolbar">
    <a class="btn" href="/houses" use:link>进入染坊</a>
    <a class="btn ghost" href="/vats" use:link>管理染缸</a>
    <a class="btn ghost" href="/lots" use:link>登记染程</a>
    <a class="btn ghost" href="/checks" use:link>色牢度抽检</a>
  </div>
</div>

<style>
  .stat {
    cursor: default;
  }

  .stat[role='button'] {
    cursor: pointer;
  }

  .stat-warn {
    border-color: rgba(220, 84, 64, 0.55);
    background: linear-gradient(160deg, rgba(220, 84, 64, 0.22), rgba(60, 26, 60, 0.35));
  }

  .stat-warn .n {
    color: #ffb4a8;
  }
</style>
