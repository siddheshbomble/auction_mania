from django.http import HttpResponse
from django.template import loader
from django import forms
from django.contrib.auth.models import User
from auction_app.forms import signup
from django.db import IntegrityError 
from django.contrib.auth import authenticate, login
from django.views import View
from django.contrib.auth import logout
from django.utils.decorators import method_decorator
from django.db.models import Q
from django.utils import timezone

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from .models import UserModel,UserModelManager,ItemModel,BidModel
from django.contrib.auth.hashers import check_password

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.db.models import Max, OuterRef, Subquery
from django.utils.timezone import now

# all views here

def index(request):
    users = UserModel.objects.all().values()
    template = loader.get_template("index.html")
    context = {
        'users':users
    }
    return HttpResponse(template.render(context,request))

class signupView(View):
    def get(self, request, *args, **kwargs):
        form = signup()
        return render(request,"signup.html",{"form":form})
    
    def post(self, request, *args, **kwargs):
        form = signup(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data["password"])
            user.save()
            return redirect("login_page")
        return render(request,"signup.html",{"form":form})

class logoutView(View):
    def get(self, request, *args, **kwargs):
        return render(request, template_name="login.html")

class loginView(View):
    def get(self, request, *args, **kwargs):
        return render(request, "login.html")

    def post(self, request, *args, **kwargs):

        username=request.POST.get("username")
        password=request.POST.get("password")

        try:
            user_obj = UserModel.objects.get(username=username)
            if check_password(password, user_obj.password):
                login(request, user_obj) 
                if user_obj.is_staff:


                    return redirect("admin_auctions_list")
                else:
                    return redirect("user_auctions_list")
            else:
                raise UserModel.DoesNotExist
        except UserModel.DoesNotExist:
            return render(request, "login.html", {"error": "Invalid Credentials"})


        print(f"Authenticated user: {user_obj}")
        if not user_obj:
            return render(request, "login.html", {"error": "Invalid Credentials"})

            login(request, user_obj)
            if user_obj.is_staff:
                return redirect("admin_auctions_list")
            else:
                return redirect("user_auctions_list")

class adminView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        return render(request, template_name="admin_home.html")

class userView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        return render(request, template_name="user_home.html")

class userAuctionsListView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):

        query = request.GET.get("query")
        if query:
            item_obj = ItemModel.objects.filter(
                Q(item_name__icontains=query) & Q(soldout_price=0)
            ).order_by('-id').values()
            
        else:
            item_obj = ItemModel.objects.filter(soldout_price=0).order_by('-id').values()

        for obj in item_obj:
            item_id = obj.get("id")
            highest_bid = (
                BidModel.objects.filter(item_id=item_id)
                .aggregate(Max("bid_amount"))["bid_amount__max"]
            )

            obj["highest_bid"] = highest_bid if highest_bid is not None else 0.00
            obj["item_name"] = obj.get("item_name")
            print("-----------------> MEDIA : ", obj["item_image"])
            print("-----------------> Highest Bid: ", obj["highest_bid"])
            

        return render(
            request,
            template_name="user_auctions_list.html",
            context={"item_list": item_obj},
        )
    def post(self, request, *args, **kwargs):
        if request.POST.get("bidsubmit") and request.POST.get("item_id"):
            item_id = request.POST.get("item_id")
            item = get_object_or_404(ItemModel, id=item_id)
            if item.auction_start_date and item.auction_start_date >= timezone.now():
                messages.warning(request, "Bidding is not allowed because auction is not started yet.")
                return redirect("user_auctions_list")
            else:
                return redirect("user_bid",item_id=item_id)

class userBidView(View):
    @method_decorator(login_required)
    def get(self, request, item_id, *args, **kwargs):
        item = get_object_or_404(ItemModel, id=item_id)
        highest_bid = item.bids.first()  
        
        if timezone.now() > item.auction_end_date:  
            messages.warning(request, 'This auction has already ended.')
            return redirect("user_auctions_list")
        
        return render(request, 'user_bid.html', {
            'item': item,
            'highest_bid': highest_bid,
        })

    def post(self, request, item_id, *args, **kwargs):
        item = get_object_or_404(ItemModel, id=item_id)

        if not request.user.is_authenticated:
            messages.info(request, 'You must be logged in to place a bid.')
            return redirect("user_bid",item_id=item_id)

        try:
            bid_amount = float(request.POST.get('bid_amount'))
        except (TypeError, ValueError):
            messages.info(request, 'Invalid bid amount')
            return redirect("user_bid",item_id=item_id)

        if request.user.user_credit < bid_amount:
            messages.info(request, 'You do not have enough credit to place this bid')
            return redirect("user_bid",item_id=item_id)


        highest_bid = item.bids.aggregate(Max('bid_amount'))['bid_amount__max']
        
        if highest_bid is None and bid_amount <= item.item_start_price:
            messages.info(request, 'Bid must be higher than start price.')
            return redirect("user_bid",item_id=item_id)
        elif highest_bid is not None and bid_amount <= highest_bid:
            messages.info(request, 'Bid must be higher than the current highest bid.')
            return redirect("user_bid",item_id=item_id)

        try:
            new_bid = BidModel.objects.create(
                item=item,
                bidder=request.user.id,
                bid_amount=bid_amount
            )

            request.user.user_credit -= bid_amount
            request.user.save()  

            return redirect('user_auctions_list')  
        except IntegrityError as e:
            return HttpResponse(f"Error IntegrityError placing bid: {str(e)}", status=500)
        except Exception as e:
            return HttpResponse(f"Error Exception placing bid: {str(e)}", status=500)

class userAddCreditsView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        user_id = request.user.id
        print("------------->  USER ID : " , user_id)

        user_obj = request.user   
        return render(
            request,
            template_name="user_add_credits.html",
            context={"user_obj": user_obj}
        )

    def post(self, request, *args, **kwargs):
        user_id = request.user.id
        print("------------->  USER ID : " , user_id)

        user_obj = request.user  
        credits_to_add = request.POST.get("credits")
        if credits_to_add:
            try:
                user_obj.user_credit += int(credits_to_add)
                user_obj.save()
                print("User credits updated successfully!")
            except ValueError:
                print("Invalid credit value.")
        return render(
            request,
            template_name="user_add_credits.html",
            context={"user_obj": user_obj}
        )
        
class userOwnBidsView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):

        bid_queryset = BidModel.objects.filter(bidder=request.user.id).order_by('-bid_time')

        bid_details = []
        for bid in bid_queryset:
            bid_details.append({
                "item_image": bid.item.item_image if bid.item.item_image else None,
                "item_name": bid.item.item_name,
                "start_price": bid.item.item_start_price,
                "highest_bid": BidModel.objects.filter(item=bid.item)
                                                .aggregate(Max("bid_amount"))["bid_amount__max"],
                "your_bid": bid.bid_amount,
                "closing_date": bid.item.auction_end_date,
            })

        won_queryset = BidModel.objects.filter(
            bidder=request.user.id,
            bid_amount=Subquery(
                BidModel.objects.filter(item_id=OuterRef('item_id'))
                                .order_by('-bid_amount')
                                .values('bid_amount')[:1]
            ),
            item__auction_end_date__lt=now()
        )

        won_details = []
        for win in won_queryset:
            won_details.append({
                "item_image": win.item.item_image if win.item.item_image else None,
                "item_name": win.item.item_name,
                "start_price": win.item.item_start_price,
                "winning_bid": win.bid_amount,
                "closing_date": win.item.auction_end_date,
            })

        return render(
            request,
            "user_view_own_bids.html",
            context={
                "bid_details": bid_details,
                "won_details": won_details,
            }
        )

class adminAuctionsListView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        query = request.GET.get("query")

        if query:
            item_obj = ItemModel.objects.filter(
                item_name__icontains=query
            ).order_by('-id').values()  
        else:
            item_obj = ItemModel.objects.all().order_by('-id').values() 

  
        for obj in item_obj:
            highest_bid = (
                BidModel.objects.filter(item_id=obj["id"])
                .aggregate(Max("bid_amount"))["bid_amount__max"]
            )
            obj["highest_bid"] = highest_bid if highest_bid is not None else 0.00
            print("-----------------> MEDIA : ", obj.get("item_image"))
            print("-----------------> Highest Bid: ", obj["highest_bid"])

        return render(
            request,
            template_name="admin_auctions_list.html",
            context={"item_list": item_obj},
        )

    def post(self, request, *args, **kwargs):
        if request.POST.get("deletesubmit") and request.POST.get("item_id"):
            item_id = request.POST.get("item_id")
            item = get_object_or_404(ItemModel, id=item_id)
            if item.auction_start_date and item.auction_start_date <= timezone.now():
                messages.warning(request, "Deleting is not allowed because the auction has already started.")
                return redirect("admin_auctions_list")
            else:
                ItemModel.objects.filter(id=request.POST.get("item_id")).delete()
                messages.warning(request, "Item deleted successfuly.")

                return redirect("admin_auctions_list")
        
        
        if request.POST.get("editsubmit") and request.POST.get("item_id"):
            item_id = request.POST.get("item_id")
            item = get_object_or_404(ItemModel, id=item_id)
            if item.auction_start_date and item.auction_start_date <= timezone.now():
                messages.warning(request, "Editing is not allowed because the auction has already started.")
                return redirect("admin_auctions_list")
            else:
                return redirect("admin_add_item_with_id",item_id=item_id)

class adminItemDetailView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        #highest_bid = None
        item_id = kwargs.get('item_id')
        item = get_object_or_404(ItemModel, id=item_id)
        highest_bid = (
                BidModel.objects.filter(item_id=item_id)
                .aggregate(Max("bid_amount"))["bid_amount__max"]
            )
        if timezone.now() > item.auction_end_date:

            if highest_bid:
                item.soldout_price = highest_bid
                item.save()

            #winner_name = winning_bid.bidder if winning_bid else "No winner (no bids)"
            
            winning_bid = BidModel.objects.filter(item_id=item_id, bid_amount=highest_bid).first()
            
            if winning_bid is None:
                return render(request, 'admin_item_details.html', {
                    'item': item,
                    'highest_bid': "No bid",
                    'winner_name': "No winner (no bids)",
                    'soldout_price': item.soldout_price
                })
            else:
                winner_id = winning_bid.bidder 
                winner_name = get_object_or_404(UserModel, id=winner_id)
                winner_name = winner_name.username
                return render(request, 'admin_item_details.html', {
                'item': item,
                'highest_bid': highest_bid,
                'winner_name': winner_name,
                'soldout_price': item.soldout_price})
                        
            
            #return render(request, 'admin_item_details.html', {'item': item})
        print("-------------->> HIGHEST BID : ",highest_bid)
        return render(request, 'admin_item_details.html', {'item': item,"highest_bid": highest_bid}) 

class adminUsersListView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        users = UserModel.objects.filter(is_staff=False, is_superuser=False).values()
        context = {
            'users':users
        }
        return render(request, template_name="admin_users_list.html",context=context)

class adminAddItemView(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        item_obj = None
        item_id = kwargs.get('item_id')

        """if request.GET.get("id"):
            item_obj = (
                ItemModel.objects.filter(id=request.GET.get("id"))
                .values()
                .first()
            ) """
        item_obj = (
            ItemModel.objects.filter(id=item_id)
            .values()
            .first()
        )


        if item_obj and item_obj.get("item_image"):
            item_obj["item_image"] = item_obj["item_image"].split("/")[1]

            return render(
                request,
                template_name="admin_add_item.html",
                context={"item_obj": item_obj},
            )
        return render(request, "admin_add_item.html")

    def post(self, request, *args, **kwargs):

        #item_id = request.GET.get("id")
        item_id = kwargs.get('item_id')
        
        if item_id:
            item_obj = ItemModel.objects.get(id=item_id)
            item_obj.item_name = request.POST.get("itemname")
            item_obj.owner_name = request.POST.get("ownername")
            item_obj.item_description = request.POST.get("description")
            item_obj.item_start_price = request.POST.get("startprice")
            item_obj.auction_start_date = request.POST.get("startdate")
            item_obj.auction_end_date = request.POST.get("enddate")

            if request.FILES.get("itemimage"):
                item_obj.item_image = request.FILES.get("itemimage")
        

            item_obj.save()  
            return redirect("admin_auctions_list")  

        else:
            ItemModel.objects.create(
                item_name=request.POST.get("itemname"),
                owner_name=request.POST.get("ownername"),
                item_image=request.FILES.get("itemimage"),
                item_description=request.POST.get("description"),
                item_start_price=request.POST.get("startprice"),
                auction_start_date=request.POST.get("startdate"),
                auction_end_date=request.POST.get("enddate"),
            )
            return redirect("admin_auctions_list")  

class adminAllBids(View):
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        all_bids = BidModel.objects.all().order_by('-bid_time')

        bid_details = []
        for bid in all_bids:
            bid_details.append({
                "bid_id": bid.id,
                "item_image": bid.item.item_image.url if bid.item.item_image else None,
                "item_name": bid.item.item_name,
                "bidder": UserModel.objects.get(id=bid.bidder).username if UserModel.objects.filter(id=bid.bidder).exists() else "Unknown",
                "bid_amount": bid.bid_amount,
                "bid_date_time": bid.bid_time,
            })

        return render(request, "admin_all_bids.html", {"bid_details": bid_details})

