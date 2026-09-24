<script>
  import { onMount } from 'svelte';
  import { api, toLocalInput, fromLocalInput } from '../lib/api.js';

  let lots = [];
  let rows = [];
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
  // 行内登记复测：{ id, at }
  let retestRow = null;

  async function load() {
    error = '';
    try {
      const q = onlyUnmet ? '?retestUnmet=true' : '';
      [lots, rows] = await Promise.all([api('/dye-lots'), api(`/fastness-checks${q}`)]);
      if (!form.dyeLotId && lots.length) {
        const open = lots.find((l) => !l.isClosed) || lots[0];
        form.dyeLotId = String(open.id);
      }
    } catch (e) {
      error = e.message;
    }
  }

  onMount(load);

  function lotLabel(id) {
    const lot = lots.find((x) => x.id === id);
    if (!lot) return id;
    return `${lot.recipeName} (#${lot.id})${lot.isClosed ? '·已关闭' : ''}`;
  }

  function lotClosed(id) {
    const lot = lots.find((x) => x.id === id);
    return !!(lot && lot.isClosed);
  }

  function validateForm() {
    if (Number(form.retestCount) > 0 && !form.lastRetestAt) {
      return '复测次数大于 0 时，末次复测时刻必填';
    }
    if (Number(form.retestCount) <= 0 && form.lastRetestAt) {
      return '复测次数为 0 时不得填写末次复测时刻';
    }
    if (form.lastRetestAt && fromLocalInput(form.lastRetestAt) < fromLocalInput(form.checkedAt)) {
      return '末次复测时刻不得早于抽检时刻';
    }
    return '';
  }

  async function save() {
    error = '';
    const verr = validateForm();
    if (verr) {
      error = verr;
      return;
    }
    const chosen = lots.find((l) => String(l.id) === String(form.dyeLotId));
    if (chosen && chosen.isClosed && !editing) {
      error = '染程已关闭，禁止再追加色牢度抽检';
      return;
    }
    try {
      const body = {
        dyeLotId: Number(form.dyeLotId),
        checkedAt: fromLocalInput(form.checkedAt),
        washFastness: Number(form.washFastness),
        rubFastness: Number(form.rubFastness),
        tempC: Number(form.tempC),
        notes: form.notes.trim() || null,
        retestCount: Number(form.retestCount) || 0,
        lastRetestAt: form.lastRetestAt ? fromLocalInput(form.lastRetestAt) : null,
      };
      if (editing) {
        await api(`/fastness-checks/${editing}`, { method: 'PUT', body: JSON.stringify(body) });
      } else {
        await api('/fastness-checks', { method: 'POST', body: JSON.stringify(body) });
      }
      editing = null;
      resetForm();
      await load();
    } catch (e) {
      error = e.message;
    }
  }

  function resetForm() {
    form = {
      ...form,
      checkedAt: toLocalInput(new Date().toISOString()),
      notes: '',
      retestCount: 0,
      lastRetestAt: '',
    };
  }

  function startEdit(row) {
    editing = row.id;
    retestRow = null;
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

  function startRetest(row) {
    editing = null;
    retestRow = { id: row.id, at: toLocalInput(new Date().toISOString()) };
  }

  async function saveRetest(row) {
    error = '';
    if (!retestRow.at) {
      error = '请填写末次复测时刻';
      return;
    }
    if (fromLocalInput(retestRow.at) < new Date(row.checkedAt).toISOString()) {
      error = '末次复测时刻不得早于抽检时刻';
      return;
    }
    try {
      await api(`/fastness-checks/${row.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          retestCount: row.retestCount + 1,
          lastRetestAt: fromLocalInput(retestRow.at),
        }),
      });
      retestRow = null;
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
  耐洗 1–5 级；摩擦牢度须大于 0；复测次数为非负整数，次数大于 0 时末次复测时刻必填且不得早于抽检时刻。
</p>

<div class="panel" style="margin-bottom:1rem;">
  <div class="form-grid">
    <label
      >染程
      <select bind:value={form.dyeLotId} disabled={!!editing}>
        {#each lots as lot}
          <option value={String(lot.id)} disabled={lot.isClosed}
            >{lot.recipeName} · {lot.fabricKg}kg{lot.isClosed ? ' · 已关闭' : ''}</option
          >
        {/each}
      </select>
    </label>
    <label>检测时间 <input type="datetime-local" bind:value={form.checkedAt} /></label>
    <label>耐洗 (1–5) <input type="number" min="1" max="5" bind:value={form.washFastness} /></label>
    <label>摩擦 (&gt;0) <input type="number" step="0.1" min="0.1" bind:value={form.rubFastness} /></label>
    <label>温度 ℃ <input type="number" step="0.1" bind:value={form.tempC} /></label>
    <label
      >复测次数 <input type="number" min="0" step="1" bind:value={form.retestCount}
    /></label>
    <label
      >末次复测时刻
      <input type="datetime-local" bind:value={form.lastRetestAt} />
    </label>
    <label>备注 <input bind:value={form.notes} /></label>
  </div>
  <div class="toolbar">
    <button class="btn" type="button" on:click={save}>{editing ? '保存修改' : '登记抽检'}</button>
    {#if editing}
      <button class="btn ghost" type="button" on:click={() => { editing = null; resetForm(); }}>取消</button>
    {/if}
  </div>
  {#if error}<p class="err">{error}</p>{/if}
</div>

<div class="panel">
  <div class="toolbar" style="margin-bottom:0.75rem;">
    <label style="display:flex;align-items:center;gap:0.4rem;margin:0;">
      <input type="checkbox" bind:checked={onlyUnmet} on:change={load} />
      仅看复测未达标行
    </label>
  </div>
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
          <td>{row.retestMet ? '✅' : '❌'}</td>
          <td>{row.notes || '—'}</td>
          <td class="row-actions">
            {#if retestRow && retestRow.id === row.id}
              <input type="datetime-local" bind:value={retestRow.at} />
              <button class="btn small" type="button" on:click={() => saveRetest(row)}>确认复测</button>
              <button class="btn ghost small" type="button" on:click={() => (retestRow = null)}>取消</button>
            {:else if lotClosed(row.dyeLotId)}
              <span style="color:var(--indigo-mist);font-size:0.85rem;">染程已关闭</span>
            {:else}
              <button class="btn ghost small" type="button" on:click={() => startRetest(row)}>登记复测</button>
              <button class="btn ghost small" type="button" on:click={() => startEdit(row)}>编辑</button>
              <button class="btn danger small" type="button" on:click={() => remove(row.id)}>删除</button>
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
