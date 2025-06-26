// Global variables
let currentUser = null
let items = []
let transactions = []
let cart = []

// Mock data
const mockItems = [
  { itemID: 1, itemName: "Laptop", category: "Electronics", quantity: 10, price: 999.99 },
  { itemID: 2, itemName: "Coffee Beans", category: "Food", quantity: 50, price: 12.99 },
  { itemID: 3, itemName: "Office Chair", category: "Furniture", quantity: 25, price: 199.99 },
  { itemID: 4, itemName: "Notebook", category: "Stationery", quantity: 100, price: 2.99 },
  { itemID: 5, itemName: "Smartphone", category: "Electronics", quantity: 15, price: 699.99 },
  { itemID: 6, itemName: "Desk Lamp", category: "Furniture", quantity: 30, price: 49.99 },
]

const mockTransactions = [
  {
    transactionID: 1,
    transactionDate: "2024-01-15T10:30:00",
    username: "shawaiz",
    totalAmount: 1199.98,
    discount: 50.0,
    netAmount: 1149.98,
    items: [
      { itemName: "Laptop", quantity: 1, price: 999.99, amount: 999.99 },
      { itemName: "Notebook", quantity: 67, price: 2.99, amount: 199.99 },
    ],
  },
  {
    transactionID: 2,
    transactionDate: "2024-01-14T14:20:00",
    username: "mustafa",
    totalAmount: 25.98,
    discount: 0.0,
    netAmount: 25.98,
    items: [{ itemName: "Coffee Beans", quantity: 2, price: 12.99, amount: 25.98 }],
  },
]

// Initialize dashboard
document.addEventListener("DOMContentLoaded", () => {
  try {
    // Check authentication
    const userData = localStorage.getItem("currentUser")
    if (!userData) {
      window.location.href = "index.html"
      return
    }

    currentUser = JSON.parse(userData)

    // Initialize data
    items = [...mockItems]
    transactions = [...mockTransactions]

    // Setup UI
    setupUserInterface()
    setupNavigation()
    setupPermissions()
    loadDashboardData()
    loadInventoryData()
    loadTransactionsData()
    loadPOSItems()
  } catch (error) {
    console.error("Error initializing dashboard:", error)
    localStorage.removeItem("currentUser")
    window.location.href = "index.html"
  }
})

// Setup user interface
function setupUserInterface() {
  document.getElementById("userName").textContent = currentUser.username
  document.getElementById("tenantName").textContent = currentUser.tenantName

  const rolesContainer = document.getElementById("userRoles")
  rolesContainer.innerHTML = ""
  currentUser.roles.forEach((role) => {
    const badge = document.createElement("span")
    badge.className = "role-badge"
    badge.textContent = role
    rolesContainer.appendChild(badge)
  })
}

// Setup navigation
function setupNavigation() {
  const navItems = document.querySelectorAll(".nav-item")
  navItems.forEach((item) => {
    item.addEventListener("click", function (e) {
      e.preventDefault()
      const page = this.dataset.page
      showPage(page)

      // Update active nav item
      navItems.forEach((nav) => nav.classList.remove("active"))
      this.classList.add("active")
    })
  })
}

// Show specific page
function showPage(pageId) {
  const pages = document.querySelectorAll(".page")
  pages.forEach((page) => page.classList.remove("active"))

  const targetPage = document.getElementById(pageId)
  if (targetPage) {
    targetPage.classList.add("active")
  }
}

// Setup permissions
function setupPermissions() {
  const permissions = currentUser.permissions

  // Show/hide elements based on permissions
  if (permissions.includes("Create_Item")) {
    document.querySelectorAll(".create-only").forEach((el) => (el.style.display = "block"))
  }

  if (permissions.includes("Update_Item")) {
    document.querySelectorAll(".update-only").forEach((el) => (el.style.display = "inline-block"))
  }

  if (permissions.includes("Delete_Item")) {
    document.querySelectorAll(".delete-only").forEach((el) => (el.style.display = "table-cell"))
  }

  // Admin-only features
  if (currentUser.roles.includes("Admin")) {
    document.querySelectorAll(".admin-only").forEach((el) => (el.style.display = "block"))
  }
}

// Load dashboard data
function loadDashboardData() {
  document.getElementById("totalItems").textContent = items.length
  document.getElementById("totalTransactions").textContent = transactions.length

  const totalRevenue = transactions.reduce((sum, t) => sum + t.netAmount, 0)
  document.getElementById("totalRevenue").textContent = `$${totalRevenue.toFixed(2)}`

  document.getElementById("activeUsers").textContent = "7" // Mock data

  // Load recent transactions
  const recentContainer = document.getElementById("recentTransactions")
  recentContainer.innerHTML = ""

  transactions.slice(0, 5).forEach((transaction) => {
    const div = document.createElement("div")
    div.className = "transaction-item"
    div.innerHTML = `
            <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f1f1;">
                <div>
                    <strong>#${transaction.transactionID}</strong><br>
                    <small>${new Date(transaction.transactionDate).toLocaleDateString()}</small>
                </div>
                <div style="text-align: right;">
                    <strong>$${transaction.netAmount.toFixed(2)}</strong><br>
                    <small>${transaction.username}</small>
                </div>
            </div>
        `
    recentContainer.appendChild(div)
  })

  // Load low stock items
  const lowStockContainer = document.getElementById("lowStockItems")
  lowStockContainer.innerHTML = ""

  const lowStockItems = items.filter((item) => item.quantity < 20)
  lowStockItems.forEach((item) => {
    const div = document.createElement("div")
    div.innerHTML = `
            <div style="display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f1f1;">
                <div>
                    <strong>${item.itemName}</strong><br>
                    <small>${item.category}</small>
                </div>
                <div style="text-align: right;">
                    <span style="color: #dc3545; font-weight: bold;">${item.quantity} left</span>
                </div>
            </div>
        `
    lowStockContainer.appendChild(div)
  })
}

// Load inventory data
function loadInventoryData() {
  if (!currentUser.permissions.includes("Read_Item")) {
    return
  }

  const tbody = document.getElementById("inventoryTableBody")
  tbody.innerHTML = ""

  items.forEach((item) => {
    const row = document.createElement("tr")
    row.innerHTML = `
            <td>${item.itemID}</td>
            <td>${item.itemName}</td>
            <td>${item.category}</td>
            <td>${item.quantity}</td>
            <td>$${item.price.toFixed(2)}</td>
            ${
              currentUser.permissions.includes("Delete_Item")
                ? `<td class="delete-only">
                    <button class="action-btn" onclick="deleteItem(${item.itemID})">Delete</button>
                </td>`
                : ""
            }
        `
    tbody.appendChild(row)
  })
}

// Load transactions data
function loadTransactionsData() {
  const tbody = document.getElementById("transactionsTableBody")
  tbody.innerHTML = ""

  transactions.forEach((transaction) => {
    const row = document.createElement("tr")
    row.innerHTML = `
            <td>${transaction.transactionID}</td>
            <td>${new Date(transaction.transactionDate).toLocaleDateString()}</td>
            <td>${transaction.username}</td>
            <td>${transaction.items ? transaction.items.length : 0}</td>
            <td>$${transaction.totalAmount.toFixed(2)}</td>
            <td>$${transaction.discount.toFixed(2)}</td>
            <td>$${transaction.netAmount.toFixed(2)}</td>
            <td>
                <button class="action-btn view" onclick="viewTransaction(${transaction.transactionID})">View</button>
            </td>
        `
    tbody.appendChild(row)
  })
}

// Load POS items
function loadPOSItems() {
  const itemGrid = document.getElementById("itemGrid")
  itemGrid.innerHTML = ""

  items.forEach((item) => {
    const itemCard = document.createElement("div")
    itemCard.className = "item-card"
    itemCard.innerHTML = `
            <h4>${item.itemName}</h4>
            <div class="price">$${item.price.toFixed(2)}</div>
            <div class="stock">Stock: ${item.quantity}</div>
        `
    itemCard.onclick = () => addToCart(item)
    itemGrid.appendChild(itemCard)
  })
}

// Cart functions
function addToCart(item) {
  const existingItem = cart.find((cartItem) => cartItem.itemID === item.itemID)

  if (existingItem) {
    if (existingItem.quantity < item.quantity) {
      existingItem.quantity++
    } else {
      showMessage("Not enough stock available", "error")
      return
    }
  } else {
    cart.push({
      ...item,
      quantity: 1,
    })
  }

  updateCartDisplay()
  updateTotal()
}

function updateCartDisplay() {
  const cartContainer = document.getElementById("cartItems")
  cartContainer.innerHTML = ""

  cart.forEach((item, index) => {
    const cartItem = document.createElement("div")
    cartItem.className = "cart-item"
    cartItem.innerHTML = `
            <div class="cart-item-info">
                <h5>${item.itemName}</h5>
                <div class="price">$${item.price.toFixed(2)} each</div>
            </div>
            <div class="quantity-controls">
                <button class="quantity-btn" onclick="decreaseQuantity(${index})">-</button>
                <span>${item.quantity}</span>
                <button class="quantity-btn" onclick="increaseQuantity(${index})">+</button>
                <button class="action-btn" onclick="removeFromCart(${index})" style="margin-left: 10px;">×</button>
            </div>
        `
    cartContainer.appendChild(cartItem)
  })
}

function increaseQuantity(index) {
  const cartItem = cart[index]
  const originalItem = items.find((item) => item.itemID === cartItem.itemID)

  if (cartItem.quantity < originalItem.quantity) {
    cartItem.quantity++
    updateCartDisplay()
    updateTotal()
  } else {
    showMessage("Not enough stock available", "error")
  }
}

function decreaseQuantity(index) {
  if (cart[index].quantity > 1) {
    cart[index].quantity--
    updateCartDisplay()
    updateTotal()
  }
}

function removeFromCart(index) {
  cart.splice(index, 1)
  updateCartDisplay()
  updateTotal()
}

function clearCart() {
  cart = []
  updateCartDisplay()
  updateTotal()
}

function updateTotal() {
  const subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0)
  const discount = Number.parseFloat(document.getElementById("discount")?.value) || 0
  const total = Math.max(0, subtotal - discount) // Ensure total is never negative

  document.getElementById("subtotal").textContent = `$${subtotal.toFixed(2)}`
  document.getElementById("total").textContent = `$${total.toFixed(2)}`
}

// Process transaction
function processTransaction() {
  if (cart.length === 0) {
    showMessage("Cart is empty", "error")
    return
  }

  const subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0)
  const discount = Number.parseFloat(document.getElementById("discount").value) || 0
  const total = subtotal - discount

  // Create new transaction
  const newTransaction = {
    transactionID: transactions.length + 1,
    transactionDate: new Date().toISOString(),
    username: currentUser.username,
    totalAmount: subtotal,
    discount: discount,
    netAmount: total,
    items: cart.map((item) => ({
      itemName: item.itemName,
      quantity: item.quantity,
      price: item.price,
      amount: item.price * item.quantity,
    })),
  }

  // Update inventory
  cart.forEach((cartItem) => {
    const inventoryItem = items.find((item) => item.itemID === cartItem.itemID)
    if (inventoryItem) {
      inventoryItem.quantity -= cartItem.quantity
    }
  })

  // Add transaction
  transactions.unshift(newTransaction)

  // Clear cart
  clearCart()

  // Refresh displays
  loadDashboardData()
  loadInventoryData()
  loadTransactionsData()
  loadPOSItems()

  showMessage(`Transaction #${newTransaction.transactionID} completed successfully!`)
}

// Item management functions
function showAddItemModal() {
  if (!currentUser.permissions.includes("Create_Item")) {
    showMessage("Access denied: You do not have permission to create items", "error")
    return
  }

  document.getElementById("addItemModal").style.display = "block"
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = "none"
}

// Add item form handler
document.getElementById("addItemForm")?.addEventListener("submit", function (e) {
  e.preventDefault()

  if (!currentUser.permissions.includes("Create_Item")) {
    showMessage("Access denied: You do not have permission to create items", "error")
    return
  }

  // Validate inputs
  const itemName = document.getElementById("itemName").value.trim()
  const itemCategory = document.getElementById("itemCategory").value.trim()
  const itemQuantity = Number.parseInt(document.getElementById("itemQuantity").value)
  const itemPrice = Number.parseFloat(document.getElementById("itemPrice").value)

  if (!itemName || !itemCategory || isNaN(itemQuantity) || isNaN(itemPrice) || itemQuantity < 0 || itemPrice < 0) {
    showMessage("Please fill in all fields with valid values", "error")
    return
  }

  const newItem = {
    itemID: Math.max(...items.map((item) => item.itemID), 0) + 1, // Better ID generation
    itemName: itemName,
    category: itemCategory,
    quantity: itemQuantity,
    price: itemPrice,
  }

  items.push(newItem)

  // Refresh displays
  loadInventoryData()
  loadPOSItems()
  loadDashboardData()

  // Close modal and reset form
  closeModal("addItemModal")
  this.reset()

  showMessage("Item added successfully!")
})

// Delete item function
function deleteItem(itemID) {
  if (!currentUser.permissions.includes("Delete_Item")) {
    showMessage("Access denied: You do not have permission to delete items", "error")
    return
  }

  if (confirm("Are you sure you want to delete this item?")) {
    items = items.filter((item) => item.itemID !== itemID)

    // Refresh displays
    loadInventoryData()
    loadPOSItems()
    loadDashboardData()

    showMessage("Item deleted successfully!")
  }
}

// Search items function
function searchItems() {
  const searchTerm = document.getElementById("itemSearch").value.toLowerCase()
  const itemGrid = document.getElementById("itemGrid")
  itemGrid.innerHTML = ""

  const filteredItems = items.filter(
    (item) => item.itemName.toLowerCase().includes(searchTerm) || item.category.toLowerCase().includes(searchTerm),
  )

  filteredItems.forEach((item) => {
    const itemCard = document.createElement("div")
    itemCard.className = "item-card"
    itemCard.innerHTML = `
            <h4>${item.itemName}</h4>
            <div class="price">$${item.price.toFixed(2)}</div>
            <div class="stock">Stock: ${item.quantity}</div>
        `
    itemCard.onclick = () => addToCart(item)
    itemGrid.appendChild(itemCard)
  })
}

// View transaction function
function viewTransaction(transactionID) {
  const transaction = transactions.find((t) => t.transactionID === transactionID)
  if (transaction) {
    let itemsList = ""
    if (transaction.items) {
      itemsList = transaction.items
        .map((item) => `${item.itemName} (${item.quantity}x) - $${item.amount.toFixed(2)}`)
        .join("\n")
    }

    alert(
      `Transaction #${transaction.transactionID}\n\nDate: ${new Date(transaction.transactionDate).toLocaleString()}\nUser: ${transaction.username}\nTotal: $${transaction.totalAmount.toFixed(2)}\nDiscount: $${transaction.discount.toFixed(2)}\nNet Amount: $${transaction.netAmount.toFixed(2)}\n\nItems:\n${itemsList}`,
    )
  }
}

// Filter transactions function
function filterTransactions() {
  const startDate = document.getElementById("startDate").value
  const endDate = document.getElementById("endDate").value

  // This would filter transactions in a real application
  showMessage("Transaction filtering applied")
}

// Show message function
function showMessage(message, type = "success") {
  const messageContainer = document.getElementById("messageContainer")
  const messageDiv = document.createElement("div")
  messageDiv.className = `message ${type}`
  messageDiv.textContent = message

  messageContainer.appendChild(messageDiv)

  // Remove message after 3 seconds
  setTimeout(() => {
    messageDiv.remove()
  }, 3000)
}

// Close modals when clicking outside
window.onclick = (event) => {
  const modals = document.querySelectorAll(".modal")
  modals.forEach((modal) => {
    if (event.target === modal) {
      modal.style.display = "none"
    }
  })
}

// Placeholder functions for admin features
function showAddUserModal() {
  showMessage("User management feature coming soon!")
}
