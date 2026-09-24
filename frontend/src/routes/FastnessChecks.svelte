<script>
  import { onMount } from 'svelte';
  import { api, toLocalInput, fromLocalInput } from '../lib/api.js';

  let lots = [];
  let rows = [];
  let requiredCount = 2;
  let error = '';
  let onlyUnmet = false;
  let form = {
    dyeLotId: '',
    checkedAt: toLocalInput(new Date().toISOString()),
    washFastness: 4,
    rubFastness: 3.5,
    tempC: 40,
    notes: '',
    retestCount: 0,
    lastRetestAt: '',
  };
  let editing = null;

  async function load() {
    error = '';
    try {
      const qs = onlyUnmet ? '?retestUnmet=true' : '';
      const [stats, lotRows, checkRows] = await Promise.all([
        api('/dashboard/stats'),
        api('/dye-lots'),
        api(`/fastness-checks${qs}`),
      ]);
      requiredCount = stats.requiredRetestCount;
      lots = lotRows;
      rows = checkRows;
      if (!form.dyeLotId) {
        const open = lots.find((l) => !l.closedAt);
        if (open) form.dyeLotId = String(open.id);
        else if (lots.length) form.dyeLotId = String(lots[0].id);
      }
    } catch (e) {
      error = e.message;
    }
  }

  onMount(load);

  function lotLabel(id) {
    const lot = lots.find((x) => x.id === id);
    if (!lot) return id;
    return `${lot.recipeName} (#${lot.id})${lot.closedAt ? '·已关闭' : ''}`;
  }

  function isClosed(id) {
    const lot = lots.find((x) => x.id === id);
    return lot ? !!lot.closedAt : false;
  }

  function clientValidate() {
    const n = Number(form.retestCount);
    if (!Number.isInteger(n) || n < 0) return '复测次数必须为非负整数';
    if (n > 0 && !form.lastRetestAt) return '复测次数大于 0 时，末次复测时刻必填';
    if (form.lastRetestAt && form.lastRetestAt < form.checkedAt) {
      return '末次复测时刻不得早于抽检时刻';
    }
    return '';
  }

  async function save() {
    error = '';
    const msg = clientValidate();
    if (msg) {
      error = msg;
      return;
    }
    try {
      const n = Number(form.retestCount);
      const body = {
        dyeLotId: Number(form.dyeLotId),
        checkedAt: fromLocalInput(form.checkedAt),
        washFastness: Number(form.washFastness),
        rubFastness: Number(form.rubFastness),
        tempC: Number(form.tempC),
        notes: form.notes.trim() || null,
        retestCount: n,
        lastRetestAt: n > 0 ? fromLocalInput(form.lastRetestAt) : null,
      };
      if (editing) {
        await api(`/fastness-checks/${editing}`, { method: 'PUT', body: JSON.stringify(body) });
      } else {
        await api('/fastness-checks', { method: 'POST', body: JSON.stringify(body) });
      }
      editing = null;
      form = {
        ...form,
        checkedAt: toLocalInput(new Date().toISOString()),
        notes: '',
        retestCount: 0,
        lastRetestAt: '',
      };
      await load();
    } catch (e) {
      error = e.message;
    }
  }

  function startEdit(row) {
    editing = row.id;
    form = {
      dyeLotId: String(row.dyeLotId),
      checkedAt: toLocalInput(row.checkedAt),
      washFastness: row.washFastness,
      rubFastness: row.rubFastness,
      tempC: row.tempC,
      notes: row.notes || '',
      retestCount: row.retestCount,
      lastRetestAt: row.lastRetestAt ? toLocalInput(row.lastRetestAt) : '',
    };
  }

  async function registerRetest(row) {
    error = '';
    try {
      await api(`/fastness-checks/${row.id}/retest`, {
        method: 'POST',
        body: JSON.stringify({}),
      });
      await load();
    } catch (e) {
      error = e.message;
    }
  }

  async function remove(id) {
    if (!confirm('确认删除该抽检？')) return;
    error = '';
    try {
      await api(`/fastness-checks/${id}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      error = e.message;
    }
  }
</script>

<h1 class="page-title">色牢度抽检</h1>
<p class="page-sub">
  耐洗 1–5 级；摩擦牢度须大于 0；复测次数为非负整数，次数大于 0 时末次复测时刻必填且不得早于抽检时刻。规定复测次数：{requiredCount} 次。
</p>

<div class="panel" style="margin-bottom:1rem;">
  <div class="form-grid">
    <label
      >染程
      <select bind:value={form.dyeLotId}>
        {#each lots as lot}
          <option value={String(lot.id)} disabled={!!lot.closedAt}
            >{lot.recipeName} · {lot.fabricKg}kg{lot.closedAt ? '（已关闭）' : ''}</option
          >
        {/each}
      </select>
    </label>
    <label>检测时间 <input type="datetime-local" bind:value={form.checkedAt} /></label>
    <label>耐洗 (1–5) <input type="number" min="1" max="5" bind:value={form.washFastness} /></label>
    <label>摩擦 (&gt;0) <input type="number" step="0.1" min="0.1" bind:value={form.rubFastness} /></label>
    <label>温度 ℃ <input type="number" step="0.1" bind:value={form.tempC} /></label>
    <label>复测次数 <input type="number" min="0" step="1" bind:value={form.retestCount} /></label>
    <label
      >末次复测时刻
      <input type="datetime-local" bind:value={form.lastRetestAt} />
    </label>
    <label>备注 <input bind:value={form.notes} /></label>
  </div>
  <div class="toolbar">
    <button class="btn" type="button" on:click={save}>{editing ? '保存修改' : '登记抽检'}</button>
    {#if editing}
      <button class="btn ghost" type="button" on:click={() => (editing = null)}>取消</button>
    {/if}
    <label style="margin-left:auto;display:flex;align-items:center;gap:0.4rem;font-size:0.85rem;">
      <input type="checkbox" bind:checked={onlyUnmet} on:change={load} />
      仅看复测未达标（&lt; {requiredCount} 次）
    </label>
  </div>
  {#if error}<p class="err">{error}</p>{/if}
</div>

<div class="panel">
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>染程</th>
        <th>检测时间</th>
        <th>耐洗</th>
        <th>摩擦</th>
        <th>温度</th>
        <th>复测次数</th>
        <th>末次复测</th>
        <th>达标</th>
        <th>备注</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{lotLabel(row.dyeLotId)}</td>
          <td>{new Date(row.checkedAt).toLocaleString()}</td>
          <td>{row.washFastness}</td>
          <td>{row.rubFastness}</td>
          <td>{row.tempC}℃</td>
          <td>{row.retestCount}</td>
          <td>{row.lastRetestAt ? new Date(row.lastRetestAt).toLocaleString() : '—'}</td>
          <td>
            {#if row.retestMet}
              <span style="color:var(--ok);">达标</span>
            {:else}
              <span class="badge-unmet">未达标</span>
            {/if}
          </td>
          <td>{row.notes || '—'}</td>
          <td class="row-actions">
            <button
              class="btn small"
              type="button"
              disabled={isClosed(row.dyeLotId)}
              title={isClosed(row.dyeLotId) ? '染程已关闭，禁止追加复测' : '复测次数 +1，记录当前时刻'}
              on:click={() => registerRetest(row)}>登记复测</button
            >
            <button class="btn ghost small" type="button" on:click={() => startEdit(row)}>编辑</button>
            <button class="btn danger small" type="button" on:click={() => remove(row.id)}>删除</button>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .badge-unmet {
    display: inline-block;
    padding: 0.1rem 0.45rem;
    border-radius: 3px;
    font-size: 0.75rem;
    color: #ffb4a8;
    background: rgba(220, 84, 64, 0.18);
    border: 1px solid rgba(220, 84, 64, 0.45);
  }
</style>
