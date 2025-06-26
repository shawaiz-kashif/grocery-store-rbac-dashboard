import pyodbc
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, send_file
from flask_cors import CORS
from datetime import datetime
import secrets
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch

app = Flask(__name__)
# Automatically generate a secure secret key
app.secret_key = secrets.token_hex(16)

# Enable CORS for all routes
CORS(app, supports_credentials=True)

# Updated connection string - make sure this matches your SQL Server setup
conn_str = (
    "Driver={SQL Server};"
    "Server=localhost;"
    "Database=RBAC;"
    "Trusted_Connection=yes;"
)

def get_db_connection():
    try:
        return pyodbc.connect(conn_str)
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    try:
        conn = get_db_connection()
        if not conn:
            error_message = "Database connection failed"
            return render_template('index.html', error=error_message)
            
        cursor = conn.cursor()
        
        # Get user with tenant info
        cursor.execute("""
            SELECT u.UserID, u.Username, u.PasswordHash, u.TenantID, t.TenantName
            FROM Users u
            JOIN Tenants t ON u.TenantID = t.TenantID
            WHERE u.Username = ?
        """, (username,))
        
        user_row = cursor.fetchone()
        
        # For demo purposes, we're using simple password comparison
        if user_row and user_row[2] == password:
            user_id = user_row[0]
            
            # Get user roles
            cursor.execute("""
                SELECT r.RoleName
                FROM UserRoles ur
                JOIN Roles r ON ur.RoleID = r.RoleID
                WHERE ur.UserID = ?
            """, (user_id,))
            
            roles = [row[0] for row in cursor.fetchall()]
            
            # Get user permissions
            cursor.execute("""
                SELECT DISTINCT p.PermissionName
                FROM UserRoles ur
                JOIN RolePermissions rp ON ur.RoleID = rp.RoleID
                JOIN Permissions p ON rp.PermissionID = p.PermissionID
                WHERE ur.UserID = ?
            """, (user_id,))
            
            permissions = [row[0] for row in cursor.fetchall()]
            
            # Store user data in session
            session['user'] = {
                'userID': user_id,
                'username': user_row[1],
                'tenantID': user_row[3],
                'tenantName': user_row[4],
                'roles': roles,
                'permissions': permissions
            }
            
            conn.close()
            return redirect(url_for('dashboard'))
        else:
            conn.close()
            error_message = "Invalid username or password"
            return render_template('index.html', error=error_message)
            
    except Exception as e:
        print(f"Database error: {e}")
        error_message = "Database connection error"
        return render_template('index.html', error=error_message)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('home'))
    return render_template('dashboard.html')

@app.route('/api/user')
def get_current_user():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify(session['user'])

@app.route('/api/items')
def get_items():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_permissions = session['user']['permissions']
    if 'Read_Item' not in user_permissions:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute("SELECT ItemID, ItemName, Category, Quantity, Price FROM Items")
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'ItemID': row[0],
                'ItemName': row[1],
                'Category': row[2],
                'Quantity': row[3],
                'Price': float(row[4])
            })
        
        conn.close()
        return jsonify(items)
    except Exception as e:
        print(f"Error fetching items: {e}")
        return jsonify({'error': 'Failed to fetch items'}), 500

@app.route('/api/items', methods=['POST'])
def create_item():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_permissions = session['user']['permissions']
    if 'Create_Item' not in user_permissions:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.json
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Items (ItemName, Category, Quantity, Price)
            VALUES (?, ?, ?, ?)
        """, (data['itemName'], data['category'], data['quantity'], data['price']))
        
        conn.commit()
        conn.close()
        return jsonify({'message': 'Item created successfully'})
    except Exception as e:
        print(f"Error creating item: {e}")
        return jsonify({'error': 'Failed to create item'}), 500

@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_permissions = session['user']['permissions']
    if 'Update_Item' not in user_permissions:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.json
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Items 
            SET ItemName = ?, Category = ?, Quantity = ?, Price = ?
            WHERE ItemID = ?
        """, (data['itemName'], data['category'], data['quantity'], data['price'], item_id))
        
        conn.commit()
        conn.close()
        return jsonify({'message': 'Item updated successfully'})
    except Exception as e:
        print(f"Error updating item: {e}")
        return jsonify({'error': 'Failed to update item'}), 500

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_permissions = session['user']['permissions']
    if 'Delete_Item' not in user_permissions:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Items WHERE ItemID = ?", (item_id,))
        
        conn.commit()
        conn.close()
        return jsonify({'message': 'Item deleted successfully'})
    except Exception as e:
        print(f"Error deleting item: {e}")
        return jsonify({'error': 'Failed to delete item'}), 500

@app.route('/api/transactions')
def get_transactions():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Get query parameters for filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        username_filter = request.args.get('username')
        
        # Build query with filters
        query = """
            SELECT tm.TransactionID, tm.TransactionDate, tm.Username, 
                   tm.TotalAmount, tm.Discount, tm.NetAmount
            FROM TransactionMaster tm
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND tm.TransactionDate >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND tm.TransactionDate <= ?"
            params.append(end_date + ' 23:59:59')  # Include full day
        
        if username_filter:
            query += " AND tm.Username LIKE ?"
            params.append(f'%{username_filter}%')
        
        query += " ORDER BY tm.TransactionDate DESC"
        
        cursor.execute(query, params)
        
        transactions = []
        for row in cursor.fetchall():
            transactions.append({
                'TransactionID': row[0],
                'TransactionDate': row[1].isoformat() if row[1] else None,
                'Username': row[2],
                'TotalAmount': float(row[3]) if row[3] else 0,
                'Discount': float(row[4]) if row[4] else 0,
                'NetAmount': float(row[5]) if row[5] else 0
            })
        
        conn.close()
        return jsonify(transactions)
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return jsonify({'error': 'Failed to fetch transactions'}), 500

@app.route('/api/transactions', methods=['POST'])
def create_transaction():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Insert transaction master
        cursor.execute("""
            INSERT INTO TransactionMaster (TransactionDate, Username, TotalAmount, Discount, NetAmount)
            VALUES (?, ?, ?, ?, ?)
        """, (data['transactionDate'], session['user']['username'], 
              data['totalAmount'], data['discount'], data['netAmount']))
        
        # Get the inserted transaction ID
        cursor.execute("SELECT @@IDENTITY")
        transaction_id = cursor.fetchone()[0]
        
        # Insert transaction details
        for item in data['items']:
            cursor.execute("""
                INSERT INTO TransactionDetails (TransactionID, ItemName, Quantity, Price, Amount)
                VALUES (?, ?, ?, ?, ?)
            """, (transaction_id, item['itemName'], item['quantity'], item['price'], item['amount']))
            
            # Update item quantity
            cursor.execute("""
                UPDATE Items 
                SET Quantity = Quantity - ?
                WHERE ItemName = ?
            """, (item['quantity'], item['itemName']))
        
        conn.commit()
        conn.close()
        return jsonify({'message': 'Transaction created successfully', 'transactionID': transaction_id})
    except Exception as e:
        print(f"Error creating transaction: {e}")
        return jsonify({'error': 'Failed to create transaction'}), 500

@app.route('/api/dashboard-stats')
def get_dashboard_stats():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        cursor = conn.cursor()
        
        # Get total items
        cursor.execute("SELECT COUNT(*) FROM Items")
        total_items = cursor.fetchone()[0]
        
        # Get total transactions
        cursor.execute("SELECT COUNT(*) FROM TransactionMaster")
        total_transactions = cursor.fetchone()[0]
        
        # Get total revenue
        cursor.execute("SELECT ISNULL(SUM(NetAmount), 0) FROM TransactionMaster")
        total_revenue = float(cursor.fetchone()[0])
        
        conn.close()
        return jsonify({
            'totalItems': total_items,
            'totalTransactions': total_transactions,
            'totalRevenue': total_revenue,
            'activeUsers': 4  # Static for demo
        })
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return jsonify({'error': 'Failed to fetch dashboard stats'}), 500
    
@app.route('/api/generate-invoice/<int:transaction_id>')
def generate_invoice(transaction_id):
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Get transaction master details
        cursor.execute("""
            SELECT tm.TransactionID, tm.TransactionDate, tm.Username, 
                   tm.TotalAmount, tm.Discount, tm.NetAmount
            FROM TransactionMaster tm
            WHERE tm.TransactionID = ?
        """, (transaction_id,))
        
        transaction = cursor.fetchone()
        if not transaction:
            return jsonify({'error': 'Transaction not found'}), 404
        
        # Get transaction details (items)
        cursor.execute("""
            SELECT td.ItemName, td.Quantity, td.Price, td.Amount
            FROM TransactionDetails td
            WHERE td.TransactionID = ?
        """, (transaction_id,))
        
        transaction_items = cursor.fetchall()
        
        # Generate PDF Invoice
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        )
        
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=10,
            textColor=colors.darkblue
        )
        
        # Company Header
        story.append(Paragraph("RBAC POS SYSTEM", title_style))
        story.append(Paragraph(f"<b>Tenant:</b> {session['user']['tenantName']}", header_style))
        story.append(Spacer(1, 20))
        
        # Invoice Title and Number
        invoice_title = ParagraphStyle(
            'InvoiceNumber',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=20,
            alignment=1
        )
        story.append(Paragraph(f"INVOICE #{transaction[0]:06d}", invoice_title))
        story.append(Spacer(1, 20))
        
        # Invoice Details Table
        invoice_details = [
            ['Invoice Date:', transaction[1].strftime('%Y-%m-%d %H:%M:%S') if transaction[1] else ''],
            ['Served By:', transaction[2] or ''],
            ['Transaction ID:', str(transaction[0])]
        ]
        
        details_table = Table(invoice_details, colWidths=[2*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 30))
        
        # Items Table
        story.append(Paragraph("ITEMS PURCHASED", styles['Heading3']))
        story.append(Spacer(1, 10))
        
        # Items data
        items_data = [['Item Name', 'Quantity', 'Unit Price', 'Amount']]
        
        for item in transaction_items:
            items_data.append([
                item[0] or '',  # ItemName
                str(item[1]) if item[1] else '0',  # Quantity
                f'${float(item[2]):.2f}' if item[2] else '$0.00',  # Price
                f'${float(item[3]):.2f}' if item[3] else '$0.00'   # Amount
            ])
        
        # Create items table
        items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # Align numbers to center
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),     # Align item names to left
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 30))
        
        # Totals Table
        totals_data = [
            ['Subtotal:', f'${float(transaction[3]):.2f}' if transaction[3] else '$0.00'],
            ['Discount:', f'${float(transaction[4]):.2f}' if transaction[4] else '$0.00'],
            ['TOTAL AMOUNT:', f'${float(transaction[5]):.2f}' if transaction[5] else '$0.00']
        ]
        
        totals_table = Table(totals_data, colWidths=[4*inch, 2*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 1), 'Helvetica'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 1), 12),
            ('FONTSIZE', (0, 2), (-1, 2), 14),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 2), (-1, 2), 12),
            ('LINEABOVE', (0, 2), (-1, 2), 2, colors.black),
            ('BACKGROUND', (0, 2), (-1, 2), colors.lightblue),
        ]))
        
        story.append(totals_table)
        story.append(Spacer(1, 40))
        
        # Footer
        footer_text = f"""
        <para align="center">
        <b>Thank you for your business!</b><br/>
        Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        System: RBAC POS
        </para>
        """
        story.append(Paragraph(footer_text, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        conn.close()
        
        # Return PDF file
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'invoice_{transaction[0]:06d}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error generating invoice: {e}")
        return jsonify({'error': 'Failed to generate invoice'}), 500


@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.json
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        username_filter = data.get('username', '')
        report_type = data.get('report_type', 'summary')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Build query with filters
        query = """
            SELECT tm.TransactionID, tm.TransactionDate, tm.Username, 
                   tm.TotalAmount, tm.Discount, tm.NetAmount
            FROM TransactionMaster tm
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND tm.TransactionDate >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND tm.TransactionDate <= ?"
            params.append(end_date + ' 23:59:59')
        
        if username_filter:
            query += " AND tm.Username LIKE ?"
            params.append(f'%{username_filter}%')
        
        query += " ORDER BY tm.TransactionDate DESC"
        
        cursor.execute(query, params)
        transactions = cursor.fetchall()
        
        # Generate PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Title
        story.append(Paragraph("Transaction Report", title_style))
        story.append(Spacer(1, 12))
        
        # Report Info
        report_info = f"""
        <b>Generated by:</b> {session['user']['username']}<br/>
        <b>Tenant:</b> {session['user']['tenantName']}<br/>
        <b>Generated on:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
        <b>Date Range:</b> {start_date or 'All'} to {end_date or 'All'}<br/>
        <b>User Filter:</b> {username_filter or 'All Users'}<br/>
        <b>Total Transactions:</b> {len(transactions)}
        """
        story.append(Paragraph(report_info, styles['Normal']))
        story.append(Spacer(1, 20))
        
        if transactions:
            # Calculate summary
            total_amount = sum(float(t[3]) if t[3] else 0 for t in transactions)
            total_discount = sum(float(t[4]) if t[4] else 0 for t in transactions)
            total_net = sum(float(t[5]) if t[5] else 0 for t in transactions)
            
            # Summary table
            summary_data = [
                ['Summary', 'Amount'],
                ['Total Amount', f'${total_amount:.2f}'],
                ['Total Discount', f'${total_discount:.2f}'],
                ['Net Amount', f'${total_net:.2f}']
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 20))
            
            # Detailed transactions table
            if report_type == 'detailed':
                story.append(Paragraph("Detailed Transactions", styles['Heading2']))
                story.append(Spacer(1, 12))
                
                # Transaction data
                table_data = [['ID', 'Date', 'User', 'Total', 'Discount', 'Net Amount']]
                
                for transaction in transactions:
                    table_data.append([
                        str(transaction[0]),
                        transaction[1].strftime('%Y-%m-%d %H:%M') if transaction[1] else '',
                        transaction[2] or '',
                        f'${float(transaction[3]):.2f}' if transaction[3] else '$0.00',
                        f'${float(transaction[4]):.2f}' if transaction[4] else '$0.00',
                        f'${float(transaction[5]):.2f}' if transaction[5] else '$0.00'
                    ])
                
                # Create table
                table = Table(table_data, colWidths=[0.8*inch, 1.5*inch, 1.2*inch, 1*inch, 1*inch, 1.2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                ]))
                
                story.append(table)
        else:
            story.append(Paragraph("No transactions found for the specified criteria.", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        conn.close()
        
        # Return PDF file
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'transaction_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({'error': 'Failed to generate report'}), 500

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    print("Starting RBAC POS System...")
    print("Secret key generated automatically for security")
    print("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)