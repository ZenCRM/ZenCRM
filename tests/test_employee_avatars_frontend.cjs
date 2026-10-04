const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const {createComponent} = require('./helpers/frontend_contract.cjs');

test('employee search combines account status and team filters',()=> {
    const app = createComponent();
    app.users = [{id:1,first_name:'Anna',is_active:true,team_ids:[5]}, {id:2,first_name:'Anna',is_active:false,team_ids:[5]}, {id:3,first_name:'Anna',is_active:true,team_ids:[6]}];
    app.userSearch = 'anna'; app.userTeamFilter = '5'; app.userStatusFilter = 'active';
    assert.deepEqual(Array.from(app.filteredUsers,u=>u.id),[1]);
    app.userStatusFilter = 'inactive'; assert.deepEqual(Array.from(app.filteredUsers,u=>u.id),[2]);
});

function setup(fetch) {
    const revoked = [];
    const sandbox = {window:{ZenI18n:{t:k=>k,locale:'pl'}},URL:{createObjectURL:()=> 'blob:preview',revokeObjectURL:url=>revoked.push(url)},FormData:class {append() {}},fetch,console,Date,localStorage:{setItem() {}}};
    vm.createContext(sandbox);vm.runInContext(fs.readFileSync('frontend/js/modules/people.js','utf8'),sandbox);
    const employee = {id:2,first_name:'Anna',is_active:true,avatar_url:'/old.png'};
    const app = {...sandbox.window.ZenModules.people(),token:'admin-session',user:{id:1,role:'admin'},users:[employee],teams:[{leader:{...employee},members:[{...employee}]}],modal:{view:'users',editingId:2,form:{}},notify() {}};
    app.openEmployeeAvatar(employee);
    app.selectEmployeeAvatar({target:{files:[{type:'image/jpeg',size:100}],value:'photo.jpg'}});
    return {app,revoked};
}

test('saving an employee photo updates directory, team and editing form',async()=> {
    const {app,revoked}=setup(async()=>({ok:true,json:async()=>({user:{id:2,avatar_url:'/new.png'}})}));
    await app.saveEmployeeAvatar();
    assert.equal(app.users[0].avatar_url,'/new.png');assert.equal(app.teams[0].leader.avatar_url,'/new.png');assert.equal(app.teams[0].members[0].avatar_url,'/new.png');assert.equal(app.modal.form.avatar_url,'/new.png');assert.equal(app.employeeAvatar.open,false);assert.deepEqual(revoked,['blob:preview']);
});
test('failed upload keeps preview and permits retry; duplicate save is blocked',async()=> {
    let calls=0,release;
    const {app}=setup(()=>{calls++;return new Promise(resolve=>release=resolve)});
    const save=app.saveEmployeeAvatar();await app.saveEmployeeAvatar();assert.equal(calls,1);
    release({ok:false,json:async()=>({error:'Upload failed'})});await save;
    assert.equal(app.employeeAvatar.error,'Upload failed');assert.equal(app.employeeAvatar.preview,'blob:preview');assert.equal(app.employeeAvatar.busy,false);assert.equal(app.users[0].avatar_url,'/old.png');
});
test('response from previous session cannot update employee data',async()=> {
    let release;const {app}=setup(()=>new Promise(resolve=>release=resolve));
    const save=app.saveEmployeeAvatar();app.token='new-session';release({ok:true,json:async()=>({user:{id:2,avatar_url:'/new.png'}})});await save;assert.equal(app.users[0].avatar_url,'/old.png');
});
