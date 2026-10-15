import React, { useState, useEffect } from 'react';
import {
  fetchAdminUsersApi,
  approveUserApi,
  rejectUserApi,
  deleteUserApi,
  fetchAdminStatsApi,
} from '../services/api';

export default function AdminPortal({ user, onClose }) {
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState({ total_users: 0, pending_approvals: 0, approved_users: 0, rejected_users: 0 });
  const [loading, setLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [feedbackMsg, setFeedbackMsg] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all', 'pending', 'approved', 'rejected'

  const loadData = async () => {
    setLoading(true);
    setFeedbackMsg(null);
    try {
      const [usersList, statsData] = await Promise.all([
        fetchAdminUsersApi(),
        fetchAdminStatsApi(),
      ]);
      setUsers(usersList);
      setStats(statsData);
    } catch (err) {
      console.error('Error loading admin portal data:', err);
      setFeedbackMsg({ type: 'error', text: err.message || 'Could not load admin data.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApprove = async (userId, userEmail) => {
    setActionLoadingId(userId);
    setFeedbackMsg(null);
    try {
      await approveUserApi(userId);
      setFeedbackMsg({ type: 'success', text: `Approved account for ${userEmail}. Confirmation email dispatched.` });
      await loadData();
    } catch (err) {
      setFeedbackMsg({ type: 'error', text: err.message || 'Failed to approve account.' });
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleReject = async (userId, userEmail) => {
    setActionLoadingId(userId);
    setFeedbackMsg(null);
    try {
      await rejectUserApi(userId);
      setFeedbackMsg({ type: 'success', text: `Declined account request for ${userEmail}.` });
      await loadData();
    } catch (err) {
      setFeedbackMsg({ type: 'error', text: err.message || 'Failed to decline account.' });
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDelete = async (userId, userEmail) => {
    if (!window.confirm(`Are you sure you want to permanently delete the user account for ${userEmail}?`)) {
      return;
    }
    setActionLoadingId(userId);
    setFeedbackMsg(null);
    try {
      await deleteUserApi(userId);
      setFeedbackMsg({ type: 'success', text: `Deleted user ${userEmail} from Firestore.` });
      await loadData();
    } catch (err) {
      setFeedbackMsg({ type: 'error', text: err.message || 'Failed to delete user.' });
    } finally {
      setActionLoadingId(null);
    }
  };

  const pendingUsers = users.filter((u) => u.status === 'pending');
  const filteredUsers = users.filter((u) => {
    if (filter === 'all') return true;
    return u.status === filter;
  });

  return (
    <div className="admin-portal-modal animate-fade-in" style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(15, 23, 42, 0.75)',
      backdropFilter: 'blur(8px)',
      zIndex: 9999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
    }}>
      <div className="admin-portal-card animate-scale-up" style={{
        background: '#FFFFFF',
        width: '100%',
        maxWidth: '1040px',
        maxHeight: '90vh',
        borderRadius: '16px',
        boxShadow: '0 25px 50px -12px rgba(15, 23, 42, 0.25)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        border: '1px solid #CBD5E1',
      }}>
        {/* Portal Header */}
        <div style={{
          background: 'linear-gradient(135deg, #0A192F 0%, #1E293B 100%)',
          padding: '20px 28px',
          color: '#FFFFFF',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #334155',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
              <span style={{ fontSize: '20px' }}>🛡️</span>
              <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', letterSpacing: '-0.3px', color: '#FFFFFF' }}>
                ITC Insight &bull; Administrator Governance Console
              </h2>
              <span style={{
                fontSize: '11px',
                fontWeight: '700',
                textTransform: 'uppercase',
                background: 'rgba(59, 130, 246, 0.2)',
                color: '#60A5FA',
                padding: '2px 8px',
                borderRadius: '9999px',
                border: '1px solid rgba(96, 165, 250, 0.3)'
              }}>
                Security Gate
              </span>
            </div>
            <div style={{ fontSize: '12px', color: '#94A3B8' }}>
              Logged in as Admin: <strong style={{ color: '#E2E8F0' }}>{user?.email || 'hrishikeshdeshpande23@gmail.com'}</strong> &bull; Notification Target: <span style={{ color: '#FCD34D' }}>hrishikeshdeshpande23@gmail.com</span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              type="button"
              onClick={loadData}
              disabled={loading}
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#FFFFFF',
                borderRadius: '8px',
                padding: '8px 14px',
                fontSize: '13px',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>🔄</span> Refresh
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#FCA5A5',
                borderRadius: '8px',
                padding: '8px 14px',
                fontSize: '13px',
                fontWeight: '600',
                cursor: 'pointer',
              }}
            >
              ✕ Exit Portal
            </button>
          </div>
        </div>

        {/* Portal Scrollable Body */}
        <div style={{ padding: '24px 28px', overflowY: 'auto', flex: 1, background: '#F8FAFC' }}>
          {/* Feedback Banner */}
          {feedbackMsg && (
            <div style={{
              background: feedbackMsg.type === 'success' ? '#ECFDF5' : '#FEF2F2',
              border: `1px solid ${feedbackMsg.type === 'success' ? '#A7F3D0' : '#FECACA'}`,
              color: feedbackMsg.type === 'success' ? '#065F46' : '#991B1B',
              padding: '12px 16px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: '500',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <span>{feedbackMsg.type === 'success' ? '✅' : '⚠️'}</span>
              <span>{feedbackMsg.text}</span>
            </div>
          )}

          {/* Metric Stats Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
            marginBottom: '28px'
          }}>
            <div style={{
              background: '#FFFFFF',
              border: stats.pending_approvals > 0 ? '2px solid #F59E0B' : '1px solid #E2E8F0',
              borderRadius: '12px',
              padding: '18px 20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
            }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: '#64748B', textTransform: 'uppercase', marginBottom: '6px' }}>
                Pending Authorization
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                <span style={{ fontSize: '28px', fontWeight: '800', color: stats.pending_approvals > 0 ? '#D97706' : '#0F172A' }}>
                  {stats.pending_approvals}
                </span>
                {stats.pending_approvals > 0 && (
                  <span style={{ fontSize: '11px', background: '#FEF3C7', color: '#B45309', padding: '2px 8px', borderRadius: '9999px', fontWeight: '700' }}>
                    Action Required
                  </span>
                )}
              </div>
            </div>

            <div style={{
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '12px',
              padding: '18px 20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
            }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: '#64748B', textTransform: 'uppercase', marginBottom: '6px' }}>
                Approved Executives &amp; Analysts
              </div>
              <span style={{ fontSize: '28px', fontWeight: '800', color: '#059669' }}>
                {stats.approved_users}
              </span>
            </div>

            <div style={{
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '12px',
              padding: '18px 20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
            }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: '#64748B', textTransform: 'uppercase', marginBottom: '6px' }}>
                Declined Requests
              </div>
              <span style={{ fontSize: '28px', fontWeight: '800', color: '#94A3B8' }}>
                {stats.rejected_users}
              </span>
            </div>

            <div style={{
              background: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '12px',
              padding: '18px 20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
            }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: '#64748B', textTransform: 'uppercase', marginBottom: '6px' }}>
                Total Accounts Stored
              </div>
              <span style={{ fontSize: '28px', fontWeight: '800', color: '#0F172A' }}>
                {stats.total_users}
              </span>
            </div>
          </div>

          {/* High-Priority Queue: Pending Approvals */}
          <div style={{ marginBottom: '32px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#0F172A', margin: 0 }}>
                  Pending Approval Queue
                </h3>
                {pendingUsers.length > 0 && (
                  <span style={{
                    background: '#FEF3C7',
                    color: '#B45309',
                    fontSize: '12px',
                    fontWeight: '700',
                    padding: '2px 8px',
                    borderRadius: '9999px'
                  }}>
                    {pendingUsers.length} waiting
                  </span>
                )}
              </div>
            </div>

            {pendingUsers.length === 0 ? (
              <div style={{
                background: '#FFFFFF',
                border: '1px dashed #CBD5E1',
                borderRadius: '12px',
                padding: '28px',
                textAlign: 'center',
                color: '#64748B'
              }}>
                <div style={{ fontSize: '28px', marginBottom: '8px' }}>✨</div>
                <div style={{ fontWeight: '600', color: '#334155', marginBottom: '4px' }}>
                  All caught up!
                </div>
                <div style={{ fontSize: '13px' }}>
                  There are currently no account registration requests awaiting authorization.
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {pendingUsers.map((pending) => (
                  <div
                    key={pending.id}
                    style={{
                      background: '#FFFFFF',
                      border: '1px solid #FDE68A',
                      borderLeft: '5px solid #F59E0B',
                      borderRadius: '10px',
                      padding: '16px 20px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.03)'
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <strong style={{ fontSize: '15px', color: '#0F172A' }}>
                          {pending.display_name}
                        </strong>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: '600',
                          background: '#FEF3C7',
                          color: '#B45309',
                          padding: '1px 8px',
                          borderRadius: '4px'
                        }}>
                          Pending Review
                        </span>
                      </div>
                      <div style={{ fontSize: '13px', color: '#475569', marginBottom: '2px' }}>
                        Email: <strong>{pending.email}</strong>
                      </div>
                      <div style={{ fontSize: '12px', color: '#94A3B8' }}>
                        Requested: {pending.created_at ? new Date(pending.created_at).toLocaleString() : 'Recent'}
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <button
                        type="button"
                        disabled={actionLoadingId === pending.id}
                        onClick={() => handleApprove(pending.id, pending.email)}
                        style={{
                          background: '#059669',
                          color: '#FFFFFF',
                          border: 'none',
                          borderRadius: '8px',
                          padding: '10px 18px',
                          fontSize: '13px',
                          fontWeight: '600',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          boxShadow: '0 2px 4px rgba(5, 150, 105, 0.2)'
                        }}
                      >
                        <span>✓</span> Approve Access
                      </button>
                      <button
                        type="button"
                        disabled={actionLoadingId === pending.id}
                        onClick={() => handleReject(pending.id, pending.email)}
                        style={{
                          background: '#FFFFFF',
                          color: '#DC2626',
                          border: '1px solid #FCA5A5',
                          borderRadius: '8px',
                          padding: '9px 14px',
                          fontSize: '13px',
                          fontWeight: '600',
                          cursor: 'pointer',
                        }}
                      >
                        ✕ Decline
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* All Users Directory Table */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#0F172A', margin: 0 }}>
                User Directory ({filteredUsers.length})
              </h3>
              <div style={{ display: 'flex', gap: '6px' }}>
                {['all', 'approved', 'pending', 'rejected'].map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => setFilter(f)}
                    style={{
                      background: filter === f ? '#0A192F' : '#FFFFFF',
                      color: filter === f ? '#FFFFFF' : '#475569',
                      border: '1px solid #CBD5E1',
                      borderRadius: '6px',
                      padding: '4px 10px',
                      fontSize: '12px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      textTransform: 'capitalize'
                    }}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>

            <div style={{
              background: '#FFFFFF',
              borderRadius: '12px',
              border: '1px solid #E2E8F0',
              overflow: 'hidden',
              boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
            }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: '#F1F5F9', borderBottom: '1px solid #CBD5E1', color: '#475569' }}>
                    <th style={{ padding: '12px 16px', fontWeight: '600' }}>Executive / Analyst</th>
                    <th style={{ padding: '12px 16px', fontWeight: '600' }}>Email Address</th>
                    <th style={{ padding: '12px 16px', fontWeight: '600' }}>Role</th>
                    <th style={{ padding: '12px 16px', fontWeight: '600' }}>Status</th>
                    <th style={{ padding: '12px 16px', fontWeight: '600' }}>Registered</th>
                    <th style={{ padding: '12px 16px', fontWeight: '600', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((u, i) => (
                    <tr
                      key={u.id || i}
                      style={{
                        borderBottom: '1px solid #F1F5F9',
                        background: u.status === 'pending' ? '#FEFCE8' : '#FFFFFF'
                      }}
                    >
                      <td style={{ padding: '12px 16px', fontWeight: '600', color: '#0F172A' }}>
                        {u.display_name}
                      </td>
                      <td style={{ padding: '12px 16px', color: '#334155' }}>
                        {u.email}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: '700',
                          background: u.role === 'admin' ? '#EEF2FF' : '#F1F5F9',
                          color: u.role === 'admin' ? '#4F46E5' : '#475569',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          textTransform: 'uppercase'
                        }}>
                          {u.role || 'user'}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: '700',
                          background:
                            u.status === 'approved' ? '#ECFDF5' :
                            u.status === 'pending' ? '#FEF3C7' : '#FEE2E2',
                          color:
                            u.status === 'approved' ? '#047857' :
                            u.status === 'pending' ? '#B45309' : '#B91C1C',
                          padding: '2px 8px',
                          borderRadius: '9999px',
                          textTransform: 'capitalize'
                        }}>
                          {u.status || 'approved'}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', color: '#64748B', fontSize: '12px' }}>
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : 'Active'}
                      </td>
                      <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '6px', alignItems: 'center' }}>
                          {u.status === 'pending' && (
                            <button
                              type="button"
                              onClick={() => handleApprove(u.id, u.email)}
                              style={{
                                background: '#059669',
                                color: '#FFFFFF',
                                border: 'none',
                                borderRadius: '4px',
                                padding: '4px 8px',
                                fontSize: '11px',
                                fontWeight: '600',
                                cursor: 'pointer'
                              }}
                            >
                              Approve
                            </button>
                          )}
                          {u.status === 'approved' && u.role !== 'admin' && (
                            <button
                              type="button"
                              onClick={() => handleReject(u.id, u.email)}
                              style={{
                                background: '#FFF1F2',
                                color: '#BE123C',
                                border: '1px solid #FECDD3',
                                borderRadius: '4px',
                                padding: '4px 8px',
                                fontSize: '11px',
                                fontWeight: '600',
                                cursor: 'pointer'
                              }}
                            >
                              Revoke
                            </button>
                          )}
                          {u.role !== 'admin' && (
                            <button
                              type="button"
                              onClick={() => handleDelete(u.id, u.email)}
                              title="Delete user"
                              style={{
                                background: 'transparent',
                                color: '#94A3B8',
                                border: 'none',
                                borderRadius: '4px',
                                padding: '4px 6px',
                                fontSize: '13px',
                                cursor: 'pointer'
                              }}
                            >
                              🗑️
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Portal Footer */}
        <div style={{
          background: '#FFFFFF',
          padding: '14px 28px',
          borderTop: '1px solid #E2E8F0',
          fontSize: '12px',
          color: '#64748B',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div>
            ☁️ Powered by Google Cloud Firestore &bull; Automatic notifications to <strong>hrishikeshdeshpande23@gmail.com</strong>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: '#0A192F',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 16px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Back to Strategic Chat &rarr;
          </button>
        </div>
      </div>
    </div>
  );
}

