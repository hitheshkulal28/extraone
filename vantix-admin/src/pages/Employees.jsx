import React, { useEffect, useState } from "react";
import api from "../utils/api";

const Employees = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [confirmDelete, setConfirmDelete] = useState(null); // user obj to delete
  const [showAddModal, setShowAddModal] = useState(false);
  const [newEmployeeEmail, setNewEmployeeEmail] = useState('');
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const fetchUsers = async () => {
    try {
      const res = await api.get('/users');
      if(res.data.success) setUsers(res.data.users);
    } catch(err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);


  const handleDeleteUser = async (userId) => {
    setError('');
    setSuccess('');
    try {
      const res = await api.delete(`/users/${userId}`);
      if (res.data.success) {
        setSuccess(res.data.message);
        setConfirmDelete(null);
        fetchUsers();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to remove user');
      setConfirmDelete(null);
    }
  };

  const handleRoleChange = async (userId, newRoleValue) => {
    setError('');
    setSuccess('');
    try {
      const res = await api.patch(`/users/${userId}`, { role: newRoleValue });
      if (res.data.success) {
        setSuccess(`Role updated to ${newRoleValue}`);
        fetchUsers();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to update role');
    }
  };

  const handleToggleAccess = async (userId) => {
    setError('');
    setSuccess('');
    try {
      const res = await api.put(`/users/${userId}/toggle-access`);
      if (res.data.success) {
        setSuccess(res.data.message);
        fetchUsers();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to toggle access');
    }
  };

  const handleAddEmployee = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (!newEmployeeEmail) return;
    try {
      const res = await api.post('/users', { email: newEmployeeEmail, role: 'employee' });
      if (res.data.success) {
        setSuccess(`Employee added! They can login to the extension with password: Password123`);
        setShowAddModal(false);
        setNewEmployeeEmail('');
        fetchUsers();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to add employee');
    }
  };

  return (
    <div className="grid" style={{ gap: 14 }}>
      <section className="card">
        <div className="card__head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <p className="card__title">Employee Directory</p>
            {success && <div className="toast toast--success" style={{ marginTop: 12 }}>{success}</div>}
            {error && <div className="toast toast--err" style={{ marginTop: 12 }}>{error}</div>}
            <div className="card__description" style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginTop: 4 }}>
              Employees can be added manually here or auto-onboarded when they login via extension.
            </div>
          </div>
          <button className="btn btn--primary" onClick={() => setShowAddModal(true)}>
            + Add Employee
          </button>
        </div>
        <div className="card__body">
          <table className="table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Active Platform</th>
                <th>Agent Access</th>
                <th style={{ width: 120 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user._id}>
                  <td>{user.email}</td>
                  <td>
                    <select
                      className="select"
                      value={user.role}
                      onChange={(e) => handleRoleChange(user._id, e.target.value)}
                      style={{
                        padding: "4px 8px",
                        fontSize: 12,
                        background: "var(--input-inline-bg)",
                        border: "1px solid var(--input-inline-border)",
                        borderRadius: 6,
                        color: user.role === "admin" ? "#25E6D9" : "var(--input-inline-color)",
                        cursor: "pointer",
                        minWidth: 90,
                      }}
                    >
                      <option value="employee">Employee</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{
                        width: 8, height: 8, borderRadius: "50%",
                        background: user.isOnline ? "#00E676" : "#FF3D00",
                        boxShadow: user.isOnline ? "0 0 8px #00E676" : "none"
                      }} />
                      <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                        {user.isOnline ? "Online" : "Offline"}
                      </span>
                    </div>
                  </td>
                  <td>
                    {user.isOnline && user.currentApp ? (
                      <span style={{ fontSize: "0.85rem", color: "var(--text-primary)" }}>{user.currentApp}</span>
                    ) : (
                      <span style={{ fontSize: "0.85rem", color: "var(--muted-text)" }}>-</span>
                    )}
                  </td>
                  <td>
                    <button
                      className={`btn ${user.isAuthorized ? "btn--outline" : "btn--danger"}`}
                      type="button"
                      style={{ fontSize: 11, padding: "4px 8px" }}
                      onClick={() => handleToggleAccess(user._id)}
                    >
                      {user.isAuthorized ? "Revoke Access" : "Grant Access"}
                    </button>
                  </td>
                  <td>
                    <button
                      className="btn btn--danger"
                      type="button"
                      style={{ fontSize: 12, padding: "4px 12px" }}
                      onClick={() => setConfirmDelete(user)}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && users.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ color: "var(--empty-state-text)" }}>
                    No users found
                  </td>
                </tr>
              )}
              {loading && (
                <tr>
                  <td colSpan={5} style={{ color: "var(--empty-state-text)" }}>
                    Loading…
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.55)",
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          onClick={() => setConfirmDelete(null)}
        >
          <div
            className="card"
            style={{ maxWidth: 420, margin: "auto", animation: "fadeIn 0.15s ease" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="card__head">
              <p className="card__title">Confirm removal</p>
            </div>
            <div className="card__body">
              <p style={{ color: "var(--muted-text)", marginBottom: 16, lineHeight: 1.5 }}>
                Are you sure you want to remove <strong style={{ color: "var(--text-primary)" }}>{confirmDelete.email}</strong>?
                This action cannot be undone. Their violation history will be preserved.
              </p>
              <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
                <button
                  className="btn"
                  type="button"
                  onClick={() => setConfirmDelete(null)}
                >
                  Cancel
                </button>
                <button
                  className="btn btn--danger"
                  type="button"
                  onClick={() => handleDeleteUser(confirmDelete._id)}
                >
                  Remove user
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Add Employee Modal */}
      {showAddModal && (
        <div className="modal-overlay">
          <div className="modal-content card" style={{ width: 400 }}>
            <p className="card__title">Add New Employee</p>
            <p className="card__description" style={{ marginBottom: 20 }}>
              Enter the employee's email address. They will be prompted to set a password upon first login.
            </p>
            <form onSubmit={handleAddEmployee} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <input
                type="email"
                className="input"
                placeholder="employee@yourcompany.com"
                value={newEmployeeEmail}
                onChange={(e) => setNewEmployeeEmail(e.target.value)}
                required
                autoFocus
              />
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 10 }}>
                <button type="button" className="btn btn--ghost" onClick={() => { setShowAddModal(false); setError(''); setNewEmployeeEmail(''); }}>
                  Cancel
                </button>
                <button type="submit" className="btn btn--primary">
                  Invite Employee
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

export default Employees;
