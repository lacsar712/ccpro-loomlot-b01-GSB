<script>
  import { onMount } from 'svelte';
  import { api, VAT_STATUS, toLocalInput, fromLocalInput } from '../lib/api.js';

  let vats = [];
  let rows = [];
  let requiredCount = 2;
  let openUnmetCount = 0;
  let error = '';
  // closedFilter: '' 全部 | 'open' 未关闭 | 'closed' 已关闭；onlyUnmet 叠加复测未达标
  let closedFilter = '';
  let onlyUnmet = false;
  let form = {
    vatId: '',
    recipeName: '',
    fabricKg: 20,
    startedAt: toLocalInput(new Date().toISOString()),
    operatorName: '染程操作员',
  };
  let editing = null;

  function buildQuery() {
    const p = new URLSearchParams();
    if (closedFilter === 'open') p.set('closed', 'false');
    if (closedFilter === 'closed') p.set('closed', 'true');
    if (onlyUnmet) p.set('retestUnmet', 'true');
    const s = p.toString();
    return s ? `?${s}` : '';
  }

  async function load() {
    error = '';
    try {
      const [stats, vatRows, lotRows] = await Promise.all([
        api('/dashboard/stats'),
        api('/vats'),
        api(`/dye-lots${buildQuery()}`),
      ]);
      requiredCount = stats.requiredRetestCount;
      openUnmetCount = stats.openRetestUnmetCount;
      vats = vatRows;
      rows = lotRows;
      const usable = vats.filter((v) => v.status === 'ready' || v.status === 'dyeing');
      if (!form.vatId && usable.length) form.vatId = String(usable[0].id);
      else if (!form.vatId && vats.length) form.vatId = String(vats[0].id);
    } catch (e) {
      error = e.message;
    }
  }

  onMount(load);

  function vatLabel(id) {
    const v = vats.find((x) => x.id === id);
    if (!v) return id;
    return `${v.vatCode}（${VAT_STATUS[v.status] || v.status}）`;
  }

  async function save() {
    error = '';
    try {
      const body = {
        vatId: Number(form.vatId),
        recipeName: form.recipeName.trim(),
        fabricKg: Number(form.fabricKg),
        startedAt: fromLocalInput(form.startedAt),
        operatorName: form.operatorName.trim(),
      };
      if (editing) {
        await api(`/dye-lots/${editing}`, { method: 'PUT', body: JSON.stringify(body) });
      } else {
        await api('/dye-lots', { method: 'POST', body: JSON.stringify(body) });
      }
      editing = null;
      form = {
        ...form,
        recipeName: '',
        fabricKg: 20,
        startedAt: toLocalInput(new Date().toISOString()),
      };
      await load();
    } catch (e) {
      error = e.message;
    }
  }

  function startEdit(row) {
    editing = row.id;
    form = {
      vatId: String(row.vatId),
      recipeName: row.recipeName,
      fabricKg: row.fabricKg,
      startedAt: toLocalInput(row.startedAt),
      operatorName: row.operatorName,
    };
  }

  async function closeLot(row) {
    if (!confirm(`确认关闭染程 #${row.id}（${row.recipeName}）？关闭后不能再追加色牢度。`)) return;
    error = '';
    try {
      await api(`/dye-lots/${row.id}/close`, { method: 'POST' });
      await load();
    } catch (e) {
      error = e.message;
    }
  }

  async function remove(id) {
    if (!confirm('确认删除该染程？')) return;
    error = '';
    try {
      await api(`/dye-lots/${id}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      error = e.message;
    }
  }

  // 看板预设：未关闭 + 复测未达标。该筛选下结果行数必须等于看板计数
  function showOpenUnmet() {
    closedFilter = 'open';
    onlyUnmet = true;
    load();
  }
</script>

<h1 class="page-title">染程</h1>
<p class="page-sub">
  仅 ready / dyeing 染缸可开缸；染程下至少一条色牢度复测满 {requiredCount} 次才可关闭，关闭后禁止再追加色牢度。
</p>

<div class="panel" style="margin-bottom:1rem;">
  <div class="form-grid">
    <label
      >染缸
      <select bind:value={form.vatId}>
        {#each vats as v}
          <option value={String(v.id)}
            >{v.vatCode} · {VAT_STATUS[v.status] || v.status} · {v.fiberType}</option
          >
        {/each}
      </select>
    </label>
    <label>配方名 <input bind:value={form.recipeName} /></label>
    <label>布料 kg <input type="number" step="0.1" bind:value={form.fabricKg} /></label>
    <label>开始时间 <input type="datetime-local" bind:value={form.startedAt} /></label>
    <label>操作员 <input bind:value={form.operatorName} /></label>
  </div>
  <div class="toolbar">
    <button class="btn" type="button" on:click={save}>{editing ? '保存修改' : '新建染程'}</button>
    {#if editing}
      <button class="btn ghost" type="button" on:click={() => (editing = null)}>取消</button>
    {/if}
  </div>
  {#if error}<p class="err">{error}</p>{/if}
</div>

<div class="panel">
  <div class="toolbar filters">
    <label>
      状态
      <select bind:value={closedFilter} on:change={load}>
        <option value="">全部</option>
        <option value="open">未关闭</option>
        <option value="closed">已关闭</option>
      </select>
    </label>
    <label style="display:flex;align-items:center;gap:0.4rem;font-size:0.85rem;">
      <input type="checkbox" bind:checked={onlyUnmet} on:change={load} />
      仅复测未达标
    </label>
    <button class="btn ghost small" type="button" on:click={showOpenUnmet}>
      看板口径：未关闭且复测未达标（{openUnmetCount}）
    </button>
    {#if closedFilter === 'open' && onlyUnmet}
      <span class="match-hint">当前 {rows.length} 行，应等于看板 {openUnmetCount}</span>
    {/if}
  </div>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>染缸</th>
        <th>配方</th>
        <th>布料 kg</th>
        <th>开始</th>
        <th>操作员</th>
        <th>状态</th>
        <th>复测达标</th>
        <th>未达标条数</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{vatLabel(row.vatId)}</td>
          <td>{row.recipeName}</td>
          <td>{row.fabricKg}</td>
          <td>{new Date(row.startedAt).toLocaleString()}</td>
          <td>{row.operatorName}</td>
          <td>
            {#if row.closedAt}
              <span class="badge-closed">已关闭 {new Date(row.closedAt).toLocaleString()}</span>
            {:else}
              <span class="badge-open">未关闭</span>
            {/if}
          </td>
          <td>
            {#if row.retestMet}
              <span style="color:var(--ok);">达标</span>
            {:else}
              <span class="badge-unmet">未达标</span>
            {/if}
          </td>
          <td>{row.retestUnmetCount}</td>
          <td class="row-actions">
            {#if !row.closedAt}
              <button
                class="btn small"
                type="button"
                disabled={!row.retestMet}
                title={row.retestMet ? '关闭染程' : `至少一条色牢度复测满 ${requiredCount} 次才可关闭`}
                on:click={() => closeLot(row)}>关闭</button
              >
            {/if}
            <button class="btn ghost small" type="button" on:click={() => startEdit(row)}>编辑</button>
            <button class="btn danger small" type="button" on:click={() => remove(row.id)}>删除</button>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .filters {
    margin-bottom: 0.85rem;
    gap: 0.9rem;
  }

  .match-hint {
    font-size: 0.8rem;
    color: var(--indigo-mist);
  }

  .badge-open,
  .badge-closed,
  .badge-unmet {
    display: inline-block;
    padding: 0.1rem 0.45rem;
    border-radius: 3px;
    font-size: 0.75rem;
    white-space: nowrap;
  }

  .badge-open {
    color: #9fd8b8;
    background: rgba(76, 175, 130, 0.15);
    border: 1px solid rgba(76, 175, 130, 0.4);
  }

  .badge-closed {
    color: var(--indigo-mist);
    background: rgba(160, 160, 190, 0.12);
    border: 1px solid var(--line);
  }

  .badge-unmet {
    color: #ffb4a8;
    background: rgba(220, 84, 64, 0.18);
    border: 1px solid rgba(220, 84, 64, 0.45);
  }
</style>
