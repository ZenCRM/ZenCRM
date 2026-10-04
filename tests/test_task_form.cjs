const assert=require('node:assert/strict');
const {createComponent}=require('./helpers/frontend_contract.cjs');
const app=createComponent();
app.user={id:7,first_name:'Anna',last_name:'Nowak'};
app.canRecordAction=()=>true;app.ensureLookups=()=>{};app.loadCustomFields=()=>{};
// createComponent uses the fixed 2026-10-03 clock for deterministic defaults.
const tomorrow=new Date('2026-10-03T12:00:00Z');tomorrow.setDate(tomorrow.getDate()+1);
const day=`${tomorrow.getFullYear()}-${String(tomorrow.getMonth()+1).padStart(2,'0')}-${String(tomorrow.getDate()).padStart(2,'0')}`;
for(const source of ['tasks','dashboard','clients','projects','services','leads','calendar']) {
 app.currentView=source;
 app.openModal(null,null,false,'tasks');
 assert.equal(app.modal.form.status,'todo');assert.equal(app.modal.form.priority,'medium');
 assert.equal(app.modal.form.due_date,day+'T09:00');
 assert.equal(app.taskAssigneesUI[0].user_id,7);assert.equal(app.taskAssigneesUI[0].user.first_name,'Anna');
}
app.openModal(null,null,true,'tasks',{prefill:{client_id:42,lead_id:12},lockedRelations:['client_id','lead_id']});
assert.equal(app.modal.form.client_id,42);assert.equal(app.modal.form.lead_id,12);
assert.equal(app.modal.form.status,'todo');assert.equal(app.taskAssigneesUI.length,1);
assert.equal(app.taskFormDate(1,'2026-01-01T16:45'),day+'T16:45');
app.loadTaskAssignees=()=>{};
app.openModal({id:8,status:'done',priority:'high',due_date:'2026-01-02T12:15'},null,false,'tasks');
assert.equal(app.modal.form.status,'done');assert.equal(app.modal.form.priority,'high');assert.equal(app.modal.form.due_date,'2026-01-02T12:15');
const fields=app.fieldsFor('tasks');assert.ok(fields.findIndex(f=>f.key==='due_date')<fields.findIndex(f=>f.key==='client_id'));
console.log('OK: task defaults across all entry points, local tomorrow, preserved context and edit values');
